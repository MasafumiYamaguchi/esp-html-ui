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
    examples = {
        "counter": ("counter", 320, 170, "native_smoke.cpp", "counter.ppm"),
        "ssd1306": ("oled", 128, 64, "native_ssd1306.cpp", "ssd1306.pbm"),
        "web-dashboard": ("dashboard", 320, 170, "native_dashboard.cpp", "dashboard.ppm"),
    }
    parser.add_argument("--example", choices=examples, default="counter")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    lvgl = args.lvgl.resolve()
    if not (lvgl / "lvgl.h").is_file():
        parser.error("--lvgl must contain lvgl.h")
    if json.loads((lvgl / "library.json").read_text())["version"] != "9.4.0":
        parser.error("Use the pinned LVGL 9.4.0 dependency")
    example = root / "examples" / args.example
    config = example / "config"
    name, width, height, test, preview_name = examples[args.example]
    build = root / ".build/native" / args.example
    build.mkdir(parents=True, exist_ok=True)
    for filename, content in generate(compile_document(example / "ui.html", name=name, width=width, height=height)).items():
        (build / filename).write_text(content, encoding="utf-8")

    flags = ["-O1", "-g", "-DLV_CONF_INCLUDE_SIMPLE", "-I" + str(lvgl), "-I" + str(config)]
    # All header mtimes participate in the cache key to avoid stale header builds.
    fingerprint = hashlib.sha256((repr(flags) + (config / "lv_conf.h").read_text()).encode())
    # Example configs may include shared headers from another example.
    for header in sorted((root / "examples").glob("*/config/*.h")):
        fingerprint.update(header.read_bytes())
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
    example_sources = sorted(path for path in (example / "src").glob("*.cpp") if path.name != "main.cpp")
    run(["g++", "-std=c++11", "-Wall", "-Wextra", *flags, "-I" + str(root / "runtime"), "-I" + str(build),
         str(root / "tests" / test), str(root / "runtime/EspHtmlUi.cpp"), str(build / f"{name}.cpp"),
         *(str(path) for path in example_sources),
         str(archive), "-lm", "-o", str(executable)])
    preview = build / preview_name
    print(run([str(executable), str(preview)]), end="")
    print(f"Rendered preview: {preview}")


if __name__ == "__main__":
    main()
