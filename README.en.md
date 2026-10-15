# esp-html-ui

[日本語](README.md) | [English](README.en.md)

A **UI compiler for ESP32 displays** that turns HTML/CSS into C++ for LVGL.
Define the appearance in HTML/CSS, then handle value updates and clicks in C++.
HTML/CSS is parsed on your computer at build time; the ESP32 runs the generated code and LVGL.

The project is currently in **early development (v0.1.0)**.
It supports generating screens with labels and buttons, displaying them on the device, and navigating them with physical buttons.
See the table below and the [supported features](docs/support.md) (Japanese) for the current HTML/CSS subset.
Alongside the T-Display S3 color display, an example supports **ESP32 + SSD1306 monochrome OLEDs (I²C, 128 × 64)**.
The SSD1306 example has passed build and host-rendering checks; physical OLED output has not yet been tested.

![T-Display S3 sample showing text wrapping and RGB text colors](docs/images/layout-check.png)

This is 320 × 170 rendering data captured from the device, rather than a photograph of the display.
Physical button operation and the display have also been checked by a person.
The [hardware test results](docs/hardware-results-2026-10-15.md) (Japanese) document the automated checks and verification methods.

[Choose a display](#choose-a-display) / [Quick start](#quick-start) / [Comparison](#how-it-compares) / [C++ API](docs/getting-started.md#c-api)

## Why esp-html-ui?

**Style the screen in HTML/CSS. Drive the device in C++.**
It is intended for developers who want to edit label-and-button screens using familiar web syntax and integrate them into an ESP32 application.

- **Review screen changes as HTML/CSS diffs.** Edit structure, colors, and spacing in your usual editor, and share styles through CSS inheritance and custom properties.
- **Keep application logic in C++.** Use HTML IDs to update text and handle click events. HTML/CSS parsing happens at build time; the device runs the generated C++ and LVGL.
- **Start with color display and monochrome OLED examples.** Code generation runs before PlatformIO builds, with resolution and display drivers configured by the application. T-Display S3 also has [automated diagnostics and rendering capture](docs/hardware-testing.md) (Japanese).

## How it compares

The comparison focuses on how you describe a screen and integrate it into an application.
It is based on official documentation reviewed on October 15, 2026.

| Option | Main UI authoring approach | Application integration |
| --- | --- | --- |
| **esp-html-ui** | **A defined subset of HTML/CSS** | **Generates C++ for LVGL; includes examples for T-Display S3 and ESP32 + SSD1306** |
| [SquareLine Studio](https://docs.squareline.io/docs/introduction/typical_dev/) | Configure widgets and events in a GUI | Exports C/C++ for LVGL, among other options |
| [EEZ Studio](https://www.envox.eu/studio/studio-introduction/) | Visual editor, with optional EEZ Flow | Creates LVGL screens; Flow can also describe application logic |
| [LVGL Pro](https://lvgl.io/docs/pro/integration/using-exported-c-code) | Work with XML through an editor or CLI | Generates C for LVGL from XML |
| [lvgljs](https://github.com/lvgl/lv_binding_js) | JavaScript using concepts from React | Uses a JavaScript runtime and LVGL bindings |

Code generation and CLI automation are also available in other tools.
esp-html-ui focuses on **connecting HTML/CSS authoring to C++ application logic and ESP32 builds**.
Its current scope is screens built around labels and buttons.
If you need images, multilingual text, more input widgets, or visual editing, also check the capabilities of the other tools.
The [detailed comparison](docs/comparison.en.md) covers Evue, which also uses HTML/CSS, suggested use cases, and official sources.

## Supported features

| Area | Current support |
| --- | --- |
| Screen structure | Containers such as `div`, `section`, `header`, and `nav` |
| Text and interaction | Headings, labels, and `button`; printable ASCII text, newlines, and tabs |
| Layout | Width, height, padding, gaps, Flex direction, wrapping, and alignment |
| Styling | Colors, backgrounds, borders, rounded corners, opacity, bundled font sizes, text wrapping, and ellipsis |
| CSS resolution | Static selectors, specificity, inheritance, `!important`, custom properties, and `var()` |
| C++ integration | Lookup by ID, text updates, click callbacks, visibility and disabled state, and focus control |
| Build-time diagnostics | Diagnostics for unsupported tags, attributes, CSS properties, and values |

**The compiler translates a defined subset of HTML/CSS into LVGL.**
Layout defaults and text placement follow LVGL, so rendering may differ from a browser.
JavaScript is not executed; application behavior is implemented in C++.

Japanese fonts, images, text and selection inputs, Grid, dynamic CSS pseudo-classes, and CSS animations are not yet supported.
See the [support reference](docs/support.md) for accepted values, units, and browser differences, and the [specification](docs/spec.md) for planned work (both in Japanese).

## Choose a display

The compiler and C++ runtime are display-independent.
The application connects the LVGL display driver and resolution.

| Configuration | Examples | Verification |
| --- | --- | --- |
| LILYGO T-Display S3, ST7789, 320 × 170 | [counter](examples/counter), [layout-check](examples/layout-check) | Builds, host rendering, physical display and buttons |
| ESP32 Dev Module + I²C SSD1306, 128 × 64 | [ssd1306](examples/ssd1306) | Build, host rendering and pixel conversion; OLED hardware not yet tested |

See [display integration](docs/displays.en.md) for SSD1306 wiring, flashing, and porting to other displays.
The quick start below uses the hardware-tested T-Display S3.

## Quick start

### Requirements

- A standard **LILYGO T-Display S3** with an ST7789 display (170 × 320). The examples use landscape orientation at 320 × 170.
- A USB cable that supports data transfer.
- Python 3.10 or newer and Git.
- Internet access for the initial dependency and toolchain downloads.

The board configuration and hardware tests for this quick start target the standard T-Display S3.
Models with other displays, such as the AMOLED version, require different configuration.

### 1. Set up the environment

macOS / Linux:

```sh
git clone https://github.com/MasafumiYamaguchi/esp-html-ui.git
cd esp-html-ui
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . -r requirements-build.txt
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
git clone https://github.com/MasafumiYamaguchi/esp-html-ui.git
cd esp-html-ui
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e . -r requirements-build.txt
```

</details>

This installs the Python compiler and PlatformIO into the same virtual environment.
PlatformIO downloads the Arduino framework, LVGL, and display driver during the next build.
Run the remaining commands from the repository root with the virtual environment activated.

### 2. Build the example

```sh
python -m platformio run -d examples/counter
```

Before compilation, the build validates `ui.html` and `ui.css` and automatically generates C++ for LVGL.
The first build takes longer because it downloads the toolchain and compiles the libraries.
Unsupported input produces a diagnostic and stops the build.

### 3. Flash the device over USB

```sh
python -m platformio device list
python -m platformio run -d examples/counter -t upload
```

If multiple devices are connected, specify a port from the list with `--upload-port`.
For example, use `--upload-port /dev/cu.usbmodem2101` on macOS or `--upload-port COM3` on Windows.

After boot, the counter displays 0 with “Count +1” focused.
Use the two physical buttons to interact with it:

| GPIO | Action |
| --- | --- |
| GPIO 0 | Move focus to the next button |
| GPIO 14 | Activate the focused button |

Press GPIO 14 to increment the counter, GPIO 0 to select “Reset,” and GPIO 14 again to reset it to 0.

## Edit the HTML/CSS

Start by changing the sample text, colors, spacing, or layout, then run the same build command again.
Code generation runs before every build, and the generated code is compiled into the firmware.

| Example | What it demonstrates | Files to edit |
| --- | --- | --- |
| [counter](examples/counter) | Increment, reset, and focus navigation | [ui.html](examples/counter/ui.html), [ui.css](examples/counter/ui.css) |
| [layout-check](examples/layout-check) | Long text wrapping, RGB text colors, and button layout | [ui.html](examples/layout-check/ui.html), [ui.css](examples/layout-check/ui.css) |
| [ssd1306](examples/ssd1306) | 128 × 64 monochrome layout, increment and reset over serial | [ui.html](examples/ssd1306/ui.html), [ui.css](examples/ssd1306/ui.css) |

To flash the layout sample shown above:

```sh
python -m platformio run -d examples/layout-check -t upload
```

Use HTML `id` attributes to access elements from C++.
See the [counter implementation](examples/counter/src/main.cpp) for event handling and the [C++ API documentation](docs/getting-started.md#c-api) (Japanese) for API contracts and element lifetimes.
The layout sample shares the same C++ implementation and substitutes different HTML/CSS.

## How it works

```text
ui.html + ui.css
       ↓ Parse, resolve CSS, and validate supported features on the host
Generated C++ + JSON generation manifest
       ↓ Compile with PlatformIO
LVGL + display driver on the ESP32
       ↓
Color display / monochrome OLED, application input
```

The compiler uses html5lib to parse HTML, tinycss2 to parse CSS, and cssselect2 to match selectors.
LVGL handles rendering, layout, and input.
TFT_eSPI transfers pixels on T-Display S3; Adafruit SSD1306 handles OLED transfers in the SSD1306 example.

You can also try compilation without connecting a device:

```sh
esp-html-ui compile examples/counter/ui.html --output build/generated --name counter
esp-html-ui support
```

The first command generates `counter.h`, `counter.cpp`, and `counter.json`.
The JSON manifest records input hashes, compiler and parser library versions, element IDs, and fonts.
The `support` command prints current and planned capabilities as JSON.

## Validation

Compiler and test-tool tests run without hardware:

```sh
python -m unittest discover -s tests -v
```

In the hardware tests on October 15, 2026, the standard counter passed 26 checks and the layout sample passed 31 checks.
The tests covered 10,000 click events, 1,000 screen creation/destruction cycles, display memory readback, repeated input, and three software reboots.
A person also confirmed normal physical button operation and display output.
See the [test results](docs/hardware-results-2026-10-15.md) for conditions and scope, and the [hardware testing guide](docs/hardware-testing.md) for reproduction steps (both in Japanese).

Host-side rendering tests using LVGL are also available.
See the [build guide](docs/getting-started.md#ホスト上での検証) (Japanese) for prerequisites and commands.

## Documentation

The detailed guides below are in Japanese unless marked otherwise.

| Document | Contents |
| --- | --- |
| [Build and usage guide](docs/getting-started.md) | Setup, generated files, pinned major dependencies, and C++ API |
| [Supported features](docs/support.md) | Tags, attributes, CSS values and limitations, and browser differences |
| [Display integration](docs/displays.en.md) (English) | SSD1306 wiring and controls, resolution settings, and porting |
| [Comparison with other UI tools](docs/comparison.en.md) (English) | Authoring formats, code generation, runtimes, and use cases |
| [Specification and completion criteria](docs/spec.md) | Project goals and planned design |
| [T-Display S3 hardware testing](docs/hardware-testing.md) | Diagnostic firmware, log and image capture, and manual button tests |
| [Hardware test results](docs/hardware-results-2026-10-15.md) | Measurements, captured rendering, and manual verification |
| [Dependencies and license management](docs/licenses.md) | Dependencies and the scope of distribution checks |
| [Third-party notices](THIRD_PARTY_NOTICES.md) (English) | License notices for dependencies and fonts |

## Reporting issues

Open a [GitHub issue](https://github.com/MasafumiYamaguchi/esp-html-ui/issues) with the commit, OS and Python versions, board model, commands, and error logs.
For compilation or layout problems, include minimal HTML/CSS that reproduces the issue and describe the expected result.
Label captured rendering data and photographs of the physical display separately.

## License

The project is published under the [MIT License](LICENSE).
This covers the compiler, C++ runtime, and project-authored examples and documentation.

Dependency and font notices are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
License checks for distributing complete firmware are ongoing, and firmware binaries are not currently released.
See [license management](docs/licenses.md) (Japanese) for details.
