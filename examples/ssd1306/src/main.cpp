#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_SSD1306.h>
#include "oled.h"
#include "ssd1306_buffer.h"

namespace {
using Ui = esphtml::generated::oled::Ui;
static_assert(Ui::width() == 128 && Ui::height() == 64, "This sample uses a 128x64 OLED");
Adafruit_SSD1306 oled(Ui::width(), Ui::height(), &Wire, OLED_RESET);
Ui ui;
alignas(4) uint8_t drawBuffer[Ui::width() * Ui::height()];
bool ready = false;
int count = 0;

uint32_t tick() { return millis(); }

void flush(lv_display_t* display, const lv_area_t*, uint8_t* pixels) {
  // FULL render mode always supplies the entire L8 frame.
  esphtml::ssd1306::copyFrame<Ui::width(), Ui::height()>(pixels, oled.getBuffer());
  oled.display();
  lv_display_flush_ready(display);
}

void updateValue() {
  char text[16];
  snprintf(text, sizeof(text), "%d", count);
  ui.setText("value", text);
}
void increment(lv_event_t*) { count = count < 999999 ? count + 1 : 0; updateValue(); }
void reset(lv_event_t*) { count = 0; updateValue(); }
} // namespace

void setup() {
  Serial.begin(115200);
  if (!Wire.begin(OLED_SDA, OLED_SCL)) {
    Serial.println("I2C initialization failed; check SDA/SCL pins");
    return;
  }
  if (!oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS, true, false)) {
    Serial.println("OLED allocation/initialization failed");
    return;
  }
  // Probe after begin() has released the optional hardware reset pin.
  Wire.beginTransmission(OLED_ADDRESS);
  if (Wire.endTransmission() != 0) {
    Serial.println("OLED did not acknowledge; check wiring and OLED_ADDRESS");
    return;
  }
  oled.clearDisplay();
  oled.display();
  lv_init();
  lv_tick_set_cb(tick);
  auto* display = lv_display_create(Ui::width(), Ui::height());
  lv_display_set_color_format(display, LV_COLOR_FORMAT_L8);
  lv_display_set_flush_cb(display, flush);
  lv_display_set_buffers(display, drawBuffer, nullptr, sizeof(drawBuffer), LV_DISPLAY_RENDER_MODE_FULL);
  if (!ui.create(lv_screen_active())) {
    Serial.println("UI creation failed");
    return;
  }
  ui.onClick("increment", increment);
  ui.onClick("reset", reset);
  for (const char* id : {"increment", "reset"}) {
    auto* button = ui.find(id);
    lv_obj_set_style_bg_color(button, lv_color_white(), LV_STATE_FOCUSED);
    lv_obj_set_style_text_color(button, lv_color_black(), LV_STATE_FOCUSED);
  }
  ui.focus("increment");
  ready = true;
  Serial.println("Ready. Send n: next button, e: activate (115200 baud).");
}

void loop() {
  if (ready) {
    while (Serial.available()) {
      const int key = Serial.read();
      if (key == 'n') lv_group_focus_next(ui.group());
      else if (key == 'e') {
        auto* button = lv_group_get_focused(ui.group());
        if (button) lv_obj_send_event(button, LV_EVENT_CLICKED, nullptr);
      }
    }
    lv_timer_handler();
  }
  delay(5);
}
