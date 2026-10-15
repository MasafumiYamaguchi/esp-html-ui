"""Exercise the diagnostic firmware without flashing or changing device settings."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import struct
import sys
import time
import zlib

EXPECTED_CHECKS = {
    "display_resolution", "flash_16mb", "psram_8mb_allocatable", "display_power",
    "ui_created", "input_group_two", "value", "increment", "reset",
    "button_geometry", "keypad_increment", "keypad_next", "keypad_reset",
    "keypad_wrap", "long_press_single_click", "counter_overflow", "disable",
    "skip_disabled", "hide", "missing_id", "ten_thousand_clicks",
    "framebuffer_background", "lcd_gram_readback", "thousand_create_clear",
    "lvgl_no_leak", "heap_no_leak",
}
LAYOUT_CHECKS = {"description_wrapped", "description_bounds", "lcd_red", "lcd_green", "lcd_blue"}


def fields(line):
    return dict(re.findall(r"(\w+)=([\w-]+)", line))


class Board:
    def __init__(self, port, output):
        import serial

        self.serial = serial.Serial()
        self.serial.port = port
        self.serial.baudrate = 115200
        self.serial.timeout = 0.25
        self.serial.write_timeout = 5
        self.serial.dtr = False
        self.serial.rts = False
        self.log = (output / "serial.log").open("wb", buffering=0)
        self.statuses = []
        self.lines = []
        self.partial_line = bytearray()
        self.serial.open()
        self.serial.reset_input_buffer()

    def close(self):
        self.serial.close()
        self.log.close()

    def line(self):
        raw = self.serial.readline()
        if not raw:
            return ""
        self.log.write(raw)
        # A serial read timeout can split one line across several reads.
        self.partial_line.extend(raw)
        if not raw.endswith(b"\n"):
            return ""
        line = self.partial_line.decode("utf-8", errors="replace").strip()
        self.partial_line.clear()
        self.lines.append(line)
        if line.startswith("STATUS "):
            self.statuses.append(fields(line))
        if any(error in line.lower() for error in (
            "guru meditation", "panic", "brownout", "harness_error", "ui creation failed",
        )):
            raise RuntimeError(line)
        if not line.startswith("STATUS "):
            print(line, flush=True)
        return line

    def wait(self, predicate, timeout=10, poll_status=False):
        deadline = time.monotonic() + timeout
        next_probe = time.monotonic() + 1
        while time.monotonic() < deadline:
            if poll_status and time.monotonic() >= next_probe:
                self.send("S")
                next_probe = time.monotonic() + 1
            line = self.line()
            if line and predicate(line):
                return line
        last = self.statuses[-1] if self.statuses else None
        raise TimeoutError(f"Expected device response did not arrive; last status: {last}")

    def send(self, command):
        self.serial.write(command.encode("ascii"))
        self.serial.flush()

    def ready(self):
        # Opening a port does not reset the chip on every host. STATUS works on
        # both a newly booted device and an already connected diagnostic build.
        deadline = time.monotonic() + 12
        next_request = 0
        while time.monotonic() < deadline:
            if time.monotonic() >= next_request:
                self.send("S")
                next_request = time.monotonic() + 0.5
            line = self.line()
            if line.startswith("STATUS ") and int(fields(line)["uptime"]) >= 1600:
                return
        raise TimeoutError("No diagnostic STATUS; flash tests/hardware first")

    def status(self):
        self.send("S")
        return fields(self.wait(lambda line: line.startswith("STATUS ")))

    def drain(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.line()


def self_test(board, layout_check=False):
    board.send("T")
    done = board.wait(lambda line: line.startswith("TEST_DONE "), 180)
    checks = {}
    for line in board.lines:
        match = re.fullmatch(r"CHECK (PASS|FAIL) (\w+)", line)
        if match:
            checks[match[2]] = match[1] == "PASS"
    expected = EXPECTED_CHECKS | (LAYOUT_CHECKS if layout_check else set())
    missing = sorted(expected - checks.keys())
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {"checks": checks, "missing": missing, "failed": failed}
    result["passed"] = fields(done).get("failures") == "0" and not missing and not failed
    return result


def memory_summary(statuses):
    return {key: sorted({int(item[key]) for item in statuses})
            for key in ("heap", "lvfree", "frag")}


def soak(board, seconds):
    start = time.monotonic()
    baseline = board.status()
    if baseline["count"] != "0" or baseline["focus"] != "increment":
        raise RuntimeError("Start the soak test with count=0 and focus=increment")
    first_status = len(board.statuses)
    rounds = 0
    while time.monotonic() - start < seconds:
        for command, expected in (
            ("E", {"count": "1", "focus": "increment"}),
            ("N", {"count": "1", "focus": "reset"}),
            ("E", {"count": "0", "focus": "reset"}),
            ("N", {"count": "0", "focus": "increment"}),
        ):
            board.send(command)
            board.wait(lambda line: line.startswith("STATUS ") and
                       all(fields(line).get(k) == v for k, v in expected.items()),
                       5, poll_status=True)
        rounds += 1
        if rounds % 10 == 0:
            print(f"SOAK rounds={rounds} seconds={time.monotonic()-start:.1f}", flush=True)
    final = board.status()
    statuses = board.statuses[first_status:]
    uptimes = [int(item["uptime"]) for item in statuses]
    rebooted = any(b < a for a, b in zip(uptimes, uptimes[1:]))
    heap_recovered = int(final["heap"]) >= int(baseline["heap"])
    lvgl_recovered = int(final["lvfree"]) >= int(baseline["lvfree"])
    return {"passed": not rebooted and heap_recovered and lvgl_recovered,
            "rounds": rounds, "injected_keys": rounds * 4,
            "elapsed_seconds": round(time.monotonic() - start, 2),
            "baseline": baseline, "final": final, "memory": memory_summary(statuses),
            "unexpected_reboot": rebooted}


def reboots(board, count):
    trials = []
    for _ in range(count):
        board.send("R")
        ready = fields(board.wait(lambda line: line.startswith("READY "), 15))
        status = board.status()
        trials.append({"ready": ready, "status": status,
                       "passed": ready.get("reset") == "3" and status.get("count") == "0"
                       and status.get("focus") == "increment" and int(status["pixels"]) >= 54400})
    return {"passed": all(trial["passed"] for trial in trials), "trials": trials}


def manual(board, seconds, optical):
    first_line = len(board.lines)
    first_status = len(board.statuses)
    print("MANUAL_READY: ENTER once, NEXT once, ENTER once; wait briefly between presses.", flush=True)
    board.drain(seconds)
    edges = [fields(line) for line in board.lines[first_line:] if line.startswith("PHYSICAL_KEY ")]
    next_pressed = any(edge.get("next") == "1" for edge in edges)
    enter_presses = 0
    was_down = False
    for edge in edges:
        down = edge.get("enter") == "1"
        enter_presses += down and not was_down
        was_down = down
    released = bool(edges) and edges[-1].get("next") == edges[-1].get("enter") == "0"
    stage = 0
    for state in board.statuses[first_status:]:
        if stage == 0 and state.get("count") == "1" and state.get("focus") == "increment":
            stage = 1
        elif stage == 1 and state.get("count") == "1" and state.get("focus") == "reset":
            stage = 2
        elif stage == 2 and state.get("count") == "0" and state.get("focus") == "reset":
            stage = 3
    buttons = next_pressed and enter_presses >= 2 and released and stage == 3
    return {"passed": buttons and optical == "confirmed", "physical_sequence_passed": buttons,
            "optical_confirmation": optical, "physical_edges": edges,
            "sequence_stage": stage, "observation_seconds": seconds,
            "status": "passed" if buttons and optical == "confirmed" else
                      "failed" if optical == "failed" else "incomplete"}


def save_frame(board, output):
    board.send("F")
    board.wait(lambda line: line.startswith("FRAME_BEGIN "))
    data = bytearray()
    deadline = time.monotonic() + 30
    while len(data) < 108800 and time.monotonic() < deadline:
        data.extend(board.serial.read(108800 - len(data)))
    if len(data) != 108800:
        raise RuntimeError(f"Incomplete frame: {len(data)} bytes")
    board.wait(lambda line: line == "FRAME_END")
    (output / "frame.rgb565").write_bytes(data)
    rgb = bytearray()
    for (pixel,) in struct.iter_unpack("<H", data):
        rgb.extend((((pixel >> 11) & 31) * 255 // 31,
                    ((pixel >> 5) & 63) * 255 // 63, (pixel & 31) * 255 // 31))

    def chunk(kind, content):
        return (struct.pack(">I", len(content)) + kind + content +
                struct.pack(">I", zlib.crc32(kind + content) & 0xffffffff))

    scanlines = b"".join(b"\0" + rgb[y * 960:(y + 1) * 960] for y in range(170))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 170, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))
    (output / "frame.png").write_bytes(png)
    return {"passed": True, "width": 320, "height": 170, "bytes": len(data),
            "image": "frame.png", "kind": "rendered pixels, not a photograph"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("test", "soak", "reboot", "manual", "frame"))
    parser.add_argument("--port", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--reboots", type=int, default=3)
    parser.add_argument("--layout-check", action="store_true",
                        help="Require the five extra checks for examples/layout-check")
    parser.add_argument("--optical", choices=("unverified", "confirmed", "failed"), default="unverified",
                        help="Only use confirmed/failed after a person inspects the display")
    args = parser.parse_args()
    if args.seconds <= 0 or args.reboots <= 0:
        parser.error("seconds and reboots must be positive")
    output = args.output or Path(".build/hardware") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    result = {"mode": args.mode, "port": args.port, "passed": False,
              "layout_check": args.layout_check,
              "started_at": datetime.now(timezone.utc).isoformat()}
    board = None
    try:
        board = Board(args.port, output)
        board.ready()
        if args.mode == "test":
            result.update(self_test(board, args.layout_check))
        elif args.mode == "soak":
            result.update(soak(board, args.seconds))
        elif args.mode == "reboot":
            result.update(reboots(board, args.reboots))
        elif args.mode == "manual":
            result.update(manual(board, args.seconds, args.optical))
        else:
            result.update(save_frame(board, output))
    except (OSError, RuntimeError, TimeoutError) as error:
        result["error"] = str(error)
    except KeyboardInterrupt:
        result["error"] = "Interrupted"
    finally:
        if board:
            board.close()
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    print(f"Evidence: {output.resolve()}", flush=True)
    return 0 if result["passed"] else 2 if result.get("status") == "incomplete" else 1


if __name__ == "__main__":
    sys.exit(main())
