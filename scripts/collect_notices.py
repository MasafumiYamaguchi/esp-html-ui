"""Collect exact upstream notices, without downloading or modifying dependencies."""
import argparse
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lvgl", type=Path, required=True)
    parser.add_argument("--tft", type=Path, required=True)
    parser.add_argument("--ssd1306", type=Path, required=True)
    parser.add_argument("--gfx", type=Path, required=True)
    parser.add_argument("--busio", type=Path, required=True)
    parser.add_argument("--webencodings-license", type=Path, required=True,
                        help="LICENSE from upstream v0.5.1; missing from PyPI wheel/sdist")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    notices = root / "third_party/notices"
    notices.mkdir(parents=True, exist_ok=True)
    inventory = []

    def save(name, data, package_version, license_name, scope, source):
        filename = name.replace("/", "_") + ".txt"
        (notices / filename).write_bytes(data)
        inventory.append({"name": name, "version": package_version, "license": license_name,
                          "scope": scope, "source": source, "notice": "notices/" + filename,
                          "sha256": hashlib.sha256(data).hexdigest()})

    for package, license_name in [("html5lib", "MIT"), ("tinycss2", "BSD-3-Clause"),
                                  ("cssselect2", "BSD-3-Clause"), ("six", "MIT")]:
        dist = distribution(package)
        found = next(file for file in dist.files if Path(str(file)).name.upper() == "LICENSE")
        save(package, dist.locate_file(found).read_bytes(), dist.version, license_name,
             "host compiler", f"PyPI {package}=={dist.version}: {found}")

    save("webencodings", args.webencodings_license.read_bytes(), "0.5.1", "BSD-3-Clause", "host compiler",
         "https://github.com/gsnedders/python-webencodings/blob/fa2cb5d75ab41e63ace691bc0825d3432ba7d694/LICENSE")

    lvgl_version = json.loads((args.lvgl / "library.json").read_text())["version"]
    tft_version = json.loads((args.tft / "library.json").read_text())["version"]
    if lvgl_version != "9.4.0" or tft_version != "2.5.43":
        raise RuntimeError("Review dependency notices before changing pinned versions")
    save("lvgl", (args.lvgl / "LICENCE.txt").read_bytes(), lvgl_version, "MIT", "firmware",
         "https://github.com/lvgl/lvgl/blob/v9.4.0/LICENCE.txt")
    save("tft_espi", (args.tft / "license.txt").read_bytes(), tft_version,
         "FreeBSD + MIT/BSD notices", "firmware",
         "TFT_eSPI 2.5.43 package: license.txt")
    for name, directory, expected, license_name, filename, repository in [
        ("adafruit_ssd1306", args.ssd1306, "2.5.15", "BSD-3-Clause", "license.txt", "Adafruit_SSD1306"),
        ("adafruit_gfx", args.gfx, "1.12.1", "BSD-2-Clause", "license.txt", "Adafruit-GFX-Library"),
        ("adafruit_busio", args.busio, "1.17.2", "MIT", "LICENSE", "Adafruit_BusIO"),
    ]:
        properties = dict(line.split("=", 1) for line in (directory / "library.properties").read_text().splitlines()
                          if "=" in line and not line.startswith("#"))
        if properties.get("version") != expected:
            raise RuntimeError(f"Review {name} notices before changing pinned versions")
        save(name, (directory / filename).read_bytes(), expected, license_name, "SSD1306 example firmware",
             f"https://github.com/adafruit/{repository}/blob/{expected}/{filename}")
    tlsf = (args.lvgl / "src/stdlib/builtin/lv_tlsf.h").read_text()
    start = tlsf.index("/*\n** Two Level")
    end = tlsf.index("*/", start) + 2
    save("lvgl_tlsf", (tlsf[start:end] + "\n").encode(), lvgl_version, "BSD-3-Clause", "firmware",
         "LVGL v9.4.0: src/stdlib/builtin/lv_tlsf.h copyright/license comment")
    save("lvgl_printf", (args.lvgl / "src/stdlib/builtin/LICENSE_SPRINTF.txt").read_bytes(),
         lvgl_version, "MIT", "firmware", "LVGL v9.4.0: src/stdlib/builtin/LICENSE_SPRINTF.txt")
    fonts = args.lvgl / "scripts/built_in_font/font_license"
    for name, relative in [("montserrat", "Montserrat/OFL.txt"), ("fontawesome5", "FontAwesome5/LICENSE.txt")]:
        save(name, (fonts / relative).read_bytes(), "bundled with LVGL 9.4.0", "OFL-1.1 (font data)",
             "firmware fonts", f"LVGL v9.4.0: scripts/built_in_font/font_license/{relative}")

    manifest = {"status": "Compiler and selected GUI components; not a complete firmware distribution audit",
                "components": inventory,
                "additional_review": ["Arduino-ESP32 LGPL-2.1-or-later components",
                                      "ESP-IDF SDK and bundled/precompiled libraries",
                                      "C/C++ runtime libraries and toolchain notices",
                                      "Build and upload tools; any newly enabled LVGL modules"]}
    (root / "third_party/dependencies.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Collected {len(inventory)} upstream notices")


if __name__ == "__main__":
    main()
