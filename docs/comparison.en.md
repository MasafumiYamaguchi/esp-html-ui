# Comparison with other UI development tools

[日本語](comparison.md) | [English](comparison.en.md)

esp-html-ui generates C++ for LVGL from HTML/CSS, with an integration workflow for T-Display S3.
It is intended for editing screen structure and styles as text while writing interaction logic in C++.
This comparison separates authoring format, generated code, and what runs on the device.

The information below is based on official documentation reviewed on October 15, 2026, and the implementation in this repository.
The other tools have not been benchmarked on the same hardware.
Suggested use cases are judgments based on the documented development approaches.

## Authoring and execution

| Option | UI input | Generation or execution model | A reason to choose it |
| --- | --- | --- | --- |
| **esp-html-ui 0.1** | A defined subset of HTML/CSS | Generates C++ at build time. The device runs generated code, the project's C++ runtime, LVGL, and the display driver | Edit label-and-button screens in HTML/CSS and integrate them into a T-Display S3 C++ application |
| [LVGL C API](https://lvgl.io/docs/open/9.4/details/widgets/index.html) | Widgets and styles defined in C/C++ | The application calls LVGL directly | Work directly with LVGL widgets and styles |
| [SquareLine Studio](https://docs.squareline.io/docs/introduction/typical_dev/) | Widgets, styles, and events configured in a GUI | Exports C files for screens, images, fonts, and other assets for integration into an application | Edit layout and events visually |
| [EEZ Studio](https://www.envox.eu/studio/studio-introduction/) | Visual editor with LVGL and LVGL + Flow project types | Creates LVGL screens; optional EEZ Flow also provides visual logic authoring | Edit screens and logic flow in an editor |
| [LVGL Pro](https://lvgl.io/docs/pro/integration/using-exported-c-code) | XML through an editor or CLI | Supports generating C from XML for application integration | Define components in XML and generate LVGL code |
| [lvgljs](https://github.com/lvgl/lv_binding_js) | JavaScript using React's virtual DOM concepts | Controls LVGL from a JavaScript environment including txiki.js and QuickJS | Describe screens and behavior in JavaScript |
| [Evue](https://github.com/scriptiot/evue) | An HTML/CSS-based evue format | Documents conversion to Python or JavaScript | Use HTML/CSS-based authoring with scripting languages or multiple UI engines |

## The workflow esp-html-ui provides

After changing colors, spacing, or layout in HTML/CSS, run the same PlatformIO build command again.
The [pre-build hook](../scripts/platformio_codegen.py) validates the supported subset and adds the generated code to the build.
The [example](../examples/counter) includes display, backlight, power, and physical button configuration for the standard T-Display S3.

Application behavior stays in C++.
The [lookup and update API](getting-started.md#c-api) (Japanese) uses HTML IDs to access text, click callbacks, and focus.
The [layout sample](../examples/layout-check) shares the counter's C++ implementation and substitutes different HTML/CSS.

Verification steps can also be shared within the repository.
The [hardware test tools](hardware-testing.md) (Japanese) cover input injection, screen creation and destruction, display memory readback, and rendering capture.
These are verification facilities provided by this project, rather than evidence of a performance advantage over other tools.

## Shared capabilities and different inputs

Several tools support code generation and build automation.
The [SquareLine Studio CLI](https://docs.squareline.io/docs/commandline/) can automate project exports.
[LVGL Pro code generation](https://lvgl.io/docs/pro/integration/using-exported-c-code) works through both the editor and CLI; when using generated C, XML files do not need to remain on the device.
esp-html-ui's approach is to parse HTML/CSS and resolve CSS on the host, then integrate generated C++ into the T-Display S3 build.

Using HTML/CSS as UI input is also not unique to esp-html-ui.
The [official Evue README](https://github.com/scriptiot/evue) describes conversion from HTML/CSS-based input to Python or JavaScript.
esp-html-ui implements C++ generation with a defined HTML/CSS subset and a T-Display S3 integration workflow.

## Current scope

If you know HTML/CSS and want to add value displays or buttons to a T-Display S3, the esp-html-ui examples provide a starting point.
They cover UI editing, updates from C++, flashing, and device verification.
See the [supported tags and CSS](support.md) and [hardware test results](hardware-results-2026-10-15.md) (both in Japanese) for the implemented and verified scope.

Text inputs, sliders, images, Japanese fonts, Grid, and dynamic CSS states are not implemented in esp-html-ui 0.1.
For visual screen editing, Flow-based logic, or JavaScript application development, consider the corresponding tools in the table.
The LVGL C API is another option when you want to use LVGL features directly.

## Official sources

- [LVGL 9.4 widget API](https://lvgl.io/docs/open/9.4/details/widgets/index.html)
- [SquareLine Studio development workflow](https://docs.squareline.io/docs/introduction/typical_dev/) and [command-line exports](https://docs.squareline.io/docs/commandline/)
- [EEZ Studio introduction and project types](https://www.envox.eu/studio/studio-introduction/)
- [LVGL Pro generated C code integration](https://lvgl.io/docs/pro/integration/using-exported-c-code)
- [Official lvgljs repository](https://github.com/lvgl/lv_binding_js)
- [Official Evue repository](https://github.com/scriptiot/evue)
