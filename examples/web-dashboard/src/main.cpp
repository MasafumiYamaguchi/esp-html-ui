#include <Arduino.h>
#include <TFT_eSPI.h>
#include "DashboardDemo.h"

namespace {
TFT_eSPI tft;
DashboardDemo demo;
alignas(4) uint8_t drawBuffer[320 * 20 * 2];
bool ready = false;

struct Key {
  explicit Key(uint8_t keyPin) : pin(keyPin) {}
  uint8_t pin;
  bool raw = false, pressed = false;
  uint32_t changedAt = 0;
  void poll(uint32_t now) {
    const bool next = digitalRead(pin) == LOW;
    if (next != raw) { raw = next; changedAt = now; }
    if (now - changedAt >= 25) pressed = raw;
  }
};
Key nextKey{0}, enterKey{14};
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
} // namespace

void setup() {
  Serial.begin(115200);
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
  auto* display = lv_display_create(320, 170);
  lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
  lv_display_set_flush_cb(display, flush);
  lv_display_set_buffers(display, drawBuffer, nullptr, sizeof(drawBuffer), LV_DISPLAY_RENDER_MODE_PARTIAL);
  if (!demo.begin(lv_screen_active())) {
    Serial.println("Dashboard creation failed");
    return;
  }
  auto* keypad = lv_indev_create();
  lv_indev_set_type(keypad, LV_INDEV_TYPE_KEYPAD);
  lv_indev_set_read_cb(keypad, readKeys);
  lv_indev_set_group(keypad, demo.ui().group());
  lv_refr_now(display);
  digitalWrite(38, HIGH);
  ready = true;
  Serial.println("DASHBOARD_READY 320x170; demo data; GPIO0=next GPIO14=activate");
}

void loop() {
  static uint32_t lastReport = 0;
  if (ready) {
    const uint32_t now = millis();
    nextKey.poll(now);
    enterKey.poll(now);
    demo.tick(now);
    lv_timer_handler();
    if (now - lastReport >= 5000) {
      Serial.printf("DASHBOARD requests=%lu automatic=%d heap=%u\n",
                    static_cast<unsigned long>(demo.requests()), demo.automatic(), ESP.getFreeHeap());
      lastReport = now;
    }
  }
  delay(5);
}
