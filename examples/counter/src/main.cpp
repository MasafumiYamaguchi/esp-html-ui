#include <Arduino.h>
#include <TFT_eSPI.h>
#include <lvgl.h>
#include "counter.h"

namespace {
TFT_eSPI tft;
esphtml::generated::counter::Ui ui;
alignas(4) uint8_t drawBuffer[320 * 20 * 2];
int count = 0;

struct Key {
  explicit Key(uint8_t keyPin) : pin(keyPin) {}
  uint8_t pin;
  bool raw = false;
  bool pressed = false;
  uint32_t changedAt = 0;
  void poll(uint32_t now) {
    const bool next = digitalRead(pin) == LOW;
    if (next != raw) { raw = next; changedAt = now; }
    if (now - changedAt >= 25) pressed = raw;
  }
};
Key nextKey{0};
Key enterKey{14};

uint32_t tick() { return millis(); }

void flush(lv_display_t* display, const lv_area_t* area, uint8_t* pixels) {
  const uint32_t width = area->x2 - area->x1 + 1;
  const uint32_t height = area->y2 - area->y1 + 1;
  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, width, height);
  tft.pushColors(reinterpret_cast<uint16_t*>(pixels), width * height, true);
  tft.endWrite();
  lv_display_flush_ready(display);
}

void readKeys(lv_indev_t*, lv_indev_data_t* data) {
  static uint32_t lastKey = LV_KEY_NEXT;
  if (nextKey.pressed) { lastKey = LV_KEY_NEXT; data->state = LV_INDEV_STATE_PRESSED; }
  else if (enterKey.pressed) { lastKey = LV_KEY_ENTER; data->state = LV_INDEV_STATE_PRESSED; }
  else data->state = LV_INDEV_STATE_RELEASED;
  data->key = lastKey;
}

void updateValue() {
  char text[24];
  snprintf(text, sizeof(text), "%d", count);
  ui.setText("value", text);
}

void increment(lv_event_t*) { count = count < 999999 ? count + 1 : 0; updateValue(); }
void reset(lv_event_t*) { count = 0; updateValue(); }
} // namespace

void setup() {
  Serial.begin(115200);
  // Enable display power on USB and battery operation.
  pinMode(15, OUTPUT);
  digitalWrite(15, HIGH);
  pinMode(38, OUTPUT);
  digitalWrite(38, LOW);
  pinMode(nextKey.pin, INPUT_PULLUP);
  pinMode(enterKey.pin, INPUT_PULLUP);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  lv_init();
  lv_tick_set_cb(tick);
  auto* display = lv_display_create(ui.width(), ui.height());
  lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
  lv_display_set_flush_cb(display, flush);
  lv_display_set_buffers(display, drawBuffer, nullptr, sizeof(drawBuffer), LV_DISPLAY_RENDER_MODE_PARTIAL);
  if (!ui.create(lv_screen_active())) { Serial.println("UI creation failed"); return; }
  ui.onClick("increment", increment);
  ui.onClick("reset", reset);
  auto* keypad = lv_indev_create();
  lv_indev_set_type(keypad, LV_INDEV_TYPE_KEYPAD);
  lv_indev_set_read_cb(keypad, readKeys);
  lv_indev_set_group(keypad, ui.group());
  ui.focus("increment");
  // remove_style_all() gives deterministic defaults; add a visible focus marker.
  for (const char* id : {"increment", "reset"}) {
    auto* object = ui.find(id);
    lv_obj_set_style_outline_width(object, 2, LV_STATE_FOCUS_KEY);
    lv_obj_set_style_outline_pad(object, 2, LV_STATE_FOCUS_KEY);
    lv_obj_set_style_outline_color(object, lv_color_hex(0x38bdf8), LV_STATE_FOCUS_KEY);
    lv_obj_set_style_bg_color(object, lv_color_hex(0x0369a1), LV_STATE_PRESSED);
  }
  digitalWrite(38, HIGH);
}

void loop() {
  const uint32_t now = millis();
  nextKey.poll(now);
  enterKey.poll(now);
  lv_timer_handler();
  delay(5);
}
