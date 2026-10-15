# Display integration

[日本語](displays.md) | [English](displays.en.md)

The compiler and C++ runtime use LVGL APIs without depending on a specific board or display driver.
The application initializes the board, transfers rendered pixels, and connects input devices.

| Example | Board and display | Resolution | Verification |
| --- | --- | --- | --- |
| [counter](../examples/counter), [layout-check](../examples/layout-check) | LILYGO T-Display S3, ST7789, TFT_eSPI | 320 × 170, RGB565 | Builds, host rendering, physical display and buttons |
| [ssd1306](../examples/ssd1306) | ESP32 Dev Module, I²C SSD1306, Adafruit SSD1306 | 128 × 64, monochrome | Build, host rendering, pixel conversion, updates and focus; OLED hardware not yet tested |

## Use an SSD1306

![Host-rendered preview of the 128 by 64 OLED screen](images/ssd1306-host.png)

This preview was rendered on the host and converted to monochrome; it is not a photograph or capture from a physical OLED.

Complete the [README environment setup](../README.en.md#1-set-up-the-environment).
This example targets a standard ESP32 Dev Module and does not require a T-Display.

### Wiring and settings

Use an I²C SSD1306 module suitable for 3.3 V operation.
Default wiring:

| OLED | ESP32 |
| --- | --- |
| GND | GND |
| VCC | 3V3 |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

Adjust `board` and `build_flags` in [platformio.ini](../examples/ssd1306/platformio.ini) for your board and wiring.
Defaults are `OLED_SDA=21`, `OLED_SCL=22`, `OLED_ADDRESS=0x3C`, and `OLED_RESET=-1`.
If using a reset pin, set `OLED_RESET` to its GPIO number.
The example checks for an ACK at the configured address and reports missing responses over serial.
An ACK does not identify the controller model.

This example is for the 128 × 64 I²C SSD1306.
SH1106 controllers, SPI modules, and 128 × 32 displays need their own driver configuration and layout adjustments.

### Build and interact

Run from the repository root with the virtual environment activated:

```sh
python -m platformio run -d examples/ssd1306
python -m platformio run -d examples/ssd1306 -t upload
python -m platformio device monitor -d examples/ssd1306
```

If multiple devices are connected, specify the upload target with `--upload-port`.
The serial monitor runs at 115200 baud.
Send `n` to focus the next button and `e` to activate it.
“+1” is initially focused: send `e` to increment, then `n` and `e` to reset.
The example uses serial input, so external buttons are not required.

### Monochrome rendering

The same compiler processes the HTML/CSS used by all examples.
The OLED layout and black-and-white palette are defined in [ui.css](../examples/ssd1306/ui.css).
LVGL renders a complete L8 grayscale frame; luminance values of 128 or higher become lit OLED pixels.
Colors and transparency ultimately become black or white, so use a black-and-white palette as your starting point.

The transfer converts row-major pixels to the SSD1306's 8-row page layout.
At 128 × 64, the LVGL draw buffer uses 8192 bytes and the driver's monochrome buffer uses 1024 bytes, in addition to LVGL objects and heap memory.
L8 rendering avoids incomplete antialiased white glyphs observed in host previews with the pinned LVGL 9.4.0 I1 rendering path.

## Port to another display

1. Configure the PlatformIO board, LVGL 9.4.0, display driver, and `config/lv_conf.h`.
2. Set `custom_ui_name`, `custom_ui_width`, and `custom_ui_height` for the generated namespace and resolution.
3. Create an LVGL display with the appropriate color format, buffers, and flush callback for the driver.
4. Create the generated UI. In the flush callback, call `lv_display_flush_ready()` after each transfer completes.
5. Connect the tick callback and any input devices.

The shared [pre-build hook](../scripts/platformio_codegen.py) assumes the `examples/<project>/` directory structure.
Defaults are `counter`, width 320, and height 170.
Output goes to `generated/<environment>/<name>/` to separate environments and UI names.
For a standalone application, you can instead add CLI-generated C++ and `runtime/` to your build.
The LVGL display and generated UI must use matching resolutions; adjust HTML/CSS for the available screen space.

## Verify without hardware

First build the example to download LVGL.
GCC/G++ or compatible Clang tools and `ar` are required.

```sh
python -m unittest discover -s tests -v
python scripts/test_native.py --lvgl examples/ssd1306/.pio/libdeps/esp32-ssd1306/lvgl --example ssd1306
```

The host test verifies layout within 128 × 64, grayscale rendering, thresholding, page layout, text updates, clicks, and focus.
It saves a preview to `.build/native/ssd1306/ssd1306.pbm`.
It does not verify I²C transfers, wiring, or output on a physical OLED.

References: [LVGL color formats](https://lvgl.io/docs/open/9.4/details/main-modules/display/color_format.html), [Adafruit SSD1306 API](https://adafruit.github.io/Adafruit_SSD1306/html/class_adafruit___s_s_d1306.html).
