# Third-party notices

The selected compiler and GUI dependency notices are preserved in [third_party/notices](third_party/notices). Versions, origins, scopes and notice hashes are recorded in [third_party/dependencies.json](third_party/dependencies.json).

| Component | License | Scope |
| --- | --- | --- |
| html5lib 1.1 | MIT | Host compiler |
| tinycss2 1.4.0 | BSD-3-Clause | Host compiler |
| cssselect2 0.8.0 | BSD-3-Clause | Host compiler |
| six 1.17.0 | MIT | Host compiler dependency |
| webencodings 0.5.1 | BSD-3-Clause | Host compiler dependency |
| LVGL 9.4.0 | MIT | Firmware GUI |
| LVGL bundled TLSF | BSD-3-Clause | Firmware allocator |
| LVGL bundled printf | MIT | Firmware formatting |
| TFT_eSPI 2.5.43 | FreeBSD and inherited MIT/BSD notices | Firmware display driver |
| Adafruit SSD1306 2.5.15 | BSD-3-Clause | SSD1306 example display driver |
| Adafruit GFX Library 1.12.1 | BSD-2-Clause | SSD1306 example driver dependency |
| Adafruit BusIO 1.17.2 | MIT | SSD1306 example driver dependency |
| Montserrat font data | SIL OFL 1.1 | LVGL built-in font data |
| Font Awesome 5 font data | SIL OFL 1.1; upstream notice includes other asset categories | Symbols bundled in LVGL's Montserrat font arrays |

The built-in LVGL Montserrat arrays contain Font Awesome glyphs even when the example uses only ASCII. Both upstream font notices are retained. TFT_eSPI's optional font packs are not enabled by the example.

The webencodings 0.5.1 PyPI wheel and source distribution omit the LICENSE file referenced in their sources. Its notice was obtained from upstream tag v0.5.1, commit `fa2cb5d75ab41e63ace691bc0825d3432ba7d694`.

## Firmware distribution review

This is a development repository, not a completed firmware distribution/license audit. Compiled firmware binaries and dependency source trees are not published here.

The Arduino-ESP32 framework includes LGPL-2.1-or-later components, including the Arduino API used by the example. An ESP-IDF SDK, precompiled libraries and C/C++ runtime libraries are also linked by PlatformIO. Before distributing firmware, inventory the actual linked components and satisfy their source, relinking, notice and other applicable requirements. A permissive license on LVGL or the compiler dependencies does not cover those components.

This file and the dependency inventory must be updated when enabling additional LVGL modules, adding fonts/images, or changing the framework or toolchain. See [license policy](docs/licenses.md).
