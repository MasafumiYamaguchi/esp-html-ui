"""Build and exercise the generated UI against the actual pinned LVGL sources."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess

from esp_html_ui.codegen import generate
from esp_html_ui.compiler import compile_document


def run(command):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(result.stdout)
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lvgl", required=True, type=Path, help="LVGL 9.4.0 source directory")
    parser.add_argument("--example", choices=["counter", "ssd1306"], default="counter")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    lvgl = args.lvgl.resolve()
    if not (lvgl / "lvgl.h").is_file():
        parser.error("--lvgl must contain lvgl.h")
    if json.loads((lvgl / "library.json").read_text())["version"] != "9.4.0":
        parser.error("Use the pinned LVGL 9.4.0 dependency")
    example = root / "examples" / args.example
    config = example / "config"
    name = "oled" if args.example == "ssd1306" else "counter"
    build = root / ".build/native" / args.example
    build.mkdir(parents=True, exist_ok=True)
    viewport = {"width": 128, "height": 64} if args.example == "ssd1306" else {}
    for filename, content in generate(compile_document(example / "ui.html", name=name, **viewport)).items():
        (build / filename).write_text(content, encoding="utf-8")

    flags = ["-O1", "-g", "-DLV_CONF_INCLUDE_SIMPLE", "-I" + str(lvgl), "-I" + str(config)]
    # All header mtimes participate in the cache key to avoid stale header builds.
    fingerprint = hashlib.sha256((repr(flags) + (config / "lv_conf.h").read_text()).encode())
    for header in sorted(lvgl.rglob("*.h")):
        stat = header.stat()
        fingerprint.update(f"{header.relative_to(lvgl)}:{stat.st_mtime_ns}:{stat.st_size}".encode())
    objects_dir = build / ("objects-" + fingerprint.hexdigest()[:12])
    objects_dir.mkdir(exist_ok=True)
    sources = sorted((lvgl / "src").rglob("*.c"))

    def compile_one(source):
        target = objects_dir / (str(source.relative_to(lvgl)).replace("/", "_") + ".o")
        if not target.exists() or target.stat().st_mtime_ns < source.stat().st_mtime_ns:
            try:
                run(["gcc", "-std=gnu99", *flags, "-c", str(source), "-o", str(target)])
            except RuntimeError:
                target.unlink(missing_ok=True)
                raise
        return target

    print(f"Building {len(sources)} LVGL C sources (cached after first run)", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as executor:
        objects = list(executor.map(compile_one, sources))
    archive = build / "liblvgl.a"
    run(["ar", "rcs", str(archive), *(str(path) for path in objects)])
    executable = build / "native_smoke"
    test = "native_ssd1306.cpp" if args.example == "ssd1306" else "native_smoke.cpp"
    run(["g++", "-std=c++11", "-Wall", "-Wextra", *flags, "-I" + str(root / "runtime"), "-I" + str(build),
         str(root / "tests" / test), str(root / "runtime/EspHtmlUi.cpp"), str(build / f"{name}.cpp"),
         str(archive), "-lm", "-o", str(executable)])
    preview = build / ("ssd1306.pbm" if args.example == "ssd1306" else "counter.ppm")
    print(run([str(executable), str(preview)]), end="")
    print(f"Rendered preview: {preview}")


if __name__ == "__main__":
    main()
