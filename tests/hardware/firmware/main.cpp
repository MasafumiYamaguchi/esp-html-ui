#define setup sampleSetup
#define loop sampleLoop
#include "../../../examples/counter/src/main.cpp"
#undef setup
#undef loop
#include <cstring>
#include <esp_system.h>
#include <utility>

// Test instrumentation shares the production example in one translation unit.
// Synthetic keys bypass GPIO polling; physical-key evidence is logged
// separately.

namespace {
uint16_t *frame;
uint32_t flushes = 0, pixelsWritten = 0, failures = 0;
bool synthetic = false;
uint32_t injectedKey = LV_KEY_ENTER;
bool injectedDown = false;
void observedFlush(lv_display_t *d, const lv_area_t *a, uint8_t *p) {
  const uint16_t *s = reinterpret_cast<uint16_t *>(p);
  for (int y = a->y1; y <= a->y2; ++y)
    for (int x = a->x1; x <= a->x2; ++x) {
      if (frame && x >= 0 && x < 320 && y >= 0 && y < 170)
        frame[y * 320 + x] = *s;
      ++s;
    }
  ++flushes;
  pixelsWritten += (a->x2 - a->x1 + 1) * (a->y2 - a->y1 + 1);
  flush(d, a, p);
}
void observedKeys(lv_indev_t *d, lv_indev_data_t *data) {
  if (synthetic) {
    data->key = injectedKey;
    data->state =
        injectedDown ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
  } else
    readKeys(d, data);
}
void check(const char *name, bool ok) {
  Serial.printf("CHECK %s %s\n", ok ? "PASS" : "FAIL", name);
  if (!ok)
    ++failures;
}
void pump(uint32_t ms) {
  uint32_t start = millis();
  while (millis() - start < ms) {
    sampleLoop();
  }
}
void key(uint32_t code, uint32_t hold = 100) {
  synthetic = true;
  injectedKey = code;
  injectedDown = true;
  pump(hold);
  injectedDown = false;
  pump(100);
  synthetic = false;
}
void status() {
  lv_mem_monitor_t m;
  lv_mem_monitor(&m);
  Serial.printf(
      "STATUS uptime=%lu count=%d focus=%s heap=%u minheap=%u lvfree=%u "
      "frag=%u flushes=%lu pixels=%lu key0=%d key14=%d failures=%lu\n",
      millis(), count,
      lv_group_get_focused(ui.group()) == ui.find("increment") ? "increment"
                                                               : "reset",
      ESP.getFreeHeap(), ESP.getMinFreeHeap(), unsigned(m.free_size),
      unsigned(m.frag_pct), flushes, pixelsWritten, digitalRead(0),
      digitalRead(14), failures);
}
uint16_t controllerPixel(int x, int y) {
  tft.setAddrWindow(x, y, 1, 1);
  uint8_t r = tft.readcommand8(0x2E, 2);
  tft.setAddrWindow(x, y, 1, 1);
  uint8_t g = tft.readcommand8(0x2E, 3);
  tft.setAddrWindow(x, y, 1, 1);
  uint8_t b = tft.readcommand8(0x2E, 4);
  Serial.printf("LCD_RAW %d %d %02x %02x %02x\n", x, y, r, g, b);
  return ((r & 0xf8) << 8) | ((g & 0xfc) << 3) | (b >> 3);
}
void runTests() {
  failures = 0;
  check("display_resolution", tft.width() == 320 && tft.height() == 170);
  check("flash_16mb", ESP.getFlashChipSize() == 16777216);
  check("psram_8mb_allocatable", psramFound() &&
                                     ESP.getPsramSize() >= (8388608 - 65536) &&
                                     ESP.getPsramSize() <= 8388608);
  check("display_power", digitalRead(15) == HIGH && digitalRead(38) == HIGH);
  check("ui_created", ui.root() && ui.find("increment") && ui.find("reset") &&
                          ui.find("value"));
  check("input_group_two", lv_group_get_obj_count(ui.group()) == 2);
  lv_obj_update_layout(ui.root());
  for (const char *id : {"value", "increment", "reset"}) {
    lv_area_t a;
    lv_obj_get_coords(ui.find(id), &a);
    Serial.printf("BOUNDS %s %d %d %d %d\n", id, a.x1, a.y1, a.x2, a.y2);
    check(id, a.x1 >= 0 && a.y1 >= 0 && a.x2 < 320 && a.y2 < 170);
  }
  check("button_geometry", lv_obj_get_width(ui.find("increment")) >= 100 &&
                               lv_obj_get_height(ui.find("increment")) == 36);
  if (auto *description = ui.find("description")) {
    lv_area_t area;
    lv_obj_get_coords(description, &area);
    check("description_wrapped", lv_obj_get_height(description) >= 28 &&
                                     lv_obj_get_height(description) <= 42);
    check("description_bounds",
          area.x1 >= 0 && area.y1 >= 0 && area.x2 < 320 && area.y2 < 170);
  }
  count = 0;
  updateValue();
  ui.focus("increment");
  pump(50);
  key(LV_KEY_ENTER);
  check("keypad_increment", count == 1);
  key(LV_KEY_NEXT);
  check("keypad_next", lv_group_get_focused(ui.group()) == ui.find("reset"));
  key(LV_KEY_ENTER);
  check("keypad_reset", count == 0);
  key(LV_KEY_NEXT);
  check("keypad_wrap",
        lv_group_get_focused(ui.group()) == ui.find("increment"));
  key(LV_KEY_ENTER, 1000);
  check("long_press_single_click", count == 1);
  count = 999999;
  updateValue();
  key(LV_KEY_ENTER);
  check("counter_overflow", count == 0);
  check("disable", ui.setDisabled("reset", true) && !ui.focus("reset"));
  key(LV_KEY_NEXT);
  check("skip_disabled",
        lv_group_get_focused(ui.group()) == ui.find("increment"));
  ui.setDisabled("reset", false);
  check("hide", ui.setHidden("reset", true) && !ui.focus("reset"));
  ui.setHidden("reset", false);
  check("missing_id", !ui.find("missing") && !ui.setText("missing", "x") &&
                          !ui.setText("value", nullptr));
  for (int i = 0; i < 10000; ++i) {
    lv_obj_send_event(ui.find("increment"), LV_EVENT_CLICKED, nullptr);
    if (i % 100 == 0) {
      lv_timer_handler();
      delay(1);
    }
  }
  check("ten_thousand_clicks",
        count == 10000 &&
            strcmp(lv_label_get_text(ui.find("value")), "10000") == 0);
  ui.focus("increment");
  count = 0;
  updateValue();
  lv_obj_invalidate(lv_screen_active());
  lv_refr_now(lv_display_get_default());
  check("framebuffer_background",
        frame && frame[0] == lv_color_to_u16(lv_color_hex(0x0f172a)));
  unsigned matches = 0;
  for (const auto &xy : {std::pair<int, int>{0, 0},
                         {319, 0},
                         {0, 169},
                         {319, 169},
                         {20, 80},
                         {300, 100}}) {
    uint16_t actual = controllerPixel(xy.first, xy.second);
    uint16_t expected = frame[xy.second * 320 + xy.first];
    Serial.printf("LCD_READ %d %d expected=%04x actual=%04x\n", xy.first,
                  xy.second, expected, actual);
    matches += actual == expected;
  }
  check("lcd_gram_readback", matches == 6);
  if (ui.find("description")) {
    const char *ids[] = {"red", "green", "blue"};
    const char *names[] = {"lcd_red", "lcd_green", "lcd_blue"};
    const uint16_t colors[] = {0xf800, 0x07e0, 0x001f};
    for (int i = 0; i < 3; ++i) {
      auto *label = ui.find(ids[i]);
      bool matched = false;
      if (label) {
        lv_area_t area;
        lv_obj_get_coords(label, &area);
        for (int y = area.y1; y <= area.y2 && !matched; ++y)
          for (int x = area.x1; x <= area.x2 && !matched; ++x)
            if (x >= 0 && x < 320 && y >= 0 && y < 170 &&
                frame[y * 320 + x] == colors[i])
              matched = controllerPixel(x, y) == colors[i];
      }
      check(names[i], matched);
    }
  }
  auto *input = lv_indev_get_next(nullptr);
  lv_indev_set_group(input, nullptr);
  ui.clear();
  lv_timer_handler();
  lv_mem_monitor_t before, after;
  lv_mem_monitor(&before);
  uint32_t heapBefore = ESP.getFreeHeap();
  bool cycles = true;
  for (int i = 0; i < 1000; ++i) {
    cycles = ui.create(lv_screen_active()) && cycles;
    ui.clear();
    if (i % 10 == 0) {
      lv_timer_handler();
      delay(1);
    }
    if (i % 100 == 0)
      Serial.printf("CYCLE %d\n", i);
  }
  lv_mem_monitor(&after);
  Serial.printf("MEMORY cycles=1000 lv_before=%u lv_after=%u heap_before=%u "
                "heap_after=%u\n",
                unsigned(before.free_size), unsigned(after.free_size),
                heapBefore, ESP.getFreeHeap());
  check("thousand_create_clear", cycles);
  check("lvgl_no_leak", before.free_size == after.free_size);
  check("heap_no_leak", ESP.getFreeHeap() >= heapBefore);
  ui.create(lv_screen_active());
  ui.onClick("increment", increment);
  ui.onClick("reset", reset);
  ui.focus("increment");
  lv_indev_set_group(input, ui.group());
  for (const char *id : {"increment", "reset"}) {
    auto *o = ui.find(id);
    lv_obj_set_style_outline_width(o, 2, LV_STATE_FOCUS_KEY);
    lv_obj_set_style_outline_pad(o, 2, LV_STATE_FOCUS_KEY);
    lv_obj_set_style_outline_color(o, lv_color_hex(0x38bdf8),
                                   LV_STATE_FOCUS_KEY);
    lv_obj_set_style_bg_color(o, lv_color_hex(0x0369a1), LV_STATE_PRESSED);
  }
  count = 0;
  updateValue();
  pump(100);
  Serial.printf("TEST_DONE failures=%lu\n", failures);
  status();
}
} // namespace
void setup() {
  sampleSetup();
  if (!ui.root() || !lv_indev_get_next(nullptr)) {
    Serial.println("HARNESS_ERROR sample initialization failed");
    while (true)
      delay(10);
  }
  frame = static_cast<uint16_t *>(ps_malloc(320 * 170 * 2));
  if (!frame)
    frame = static_cast<uint16_t *>(malloc(320 * 170 * 2));
  if (!frame) {
    Serial.println("HARNESS_ERROR framebuffer allocation failed");
    while (true)
      delay(10);
  }
  memset(frame, 0, 320 * 170 * 2);
  lv_display_set_flush_cb(lv_display_get_default(), observedFlush);
  lv_indev_set_read_cb(lv_indev_get_next(nullptr), observedKeys);
  lv_obj_invalidate(lv_screen_active());
}

void loop() {
  sampleLoop();
  static uint32_t last = 0;
  static bool announced = false;
  static bool old0 = false, old14 = false;
  static bool raw0 = false, raw14 = false;
  static int oldCount = -1;
  static lv_obj_t *oldFocus = nullptr;
  if (!announced && Serial && millis() > 1500) {
    Serial.printf("READY reset=%d chip=%s cpu=%u psram=%u flash=%u frame=%d\n",
                  esp_reset_reason(), ESP.getChipModel(), ESP.getCpuFreqMHz(),
                  ESP.getPsramSize(), ESP.getFlashChipSize(), frame != nullptr);
    status();
    announced = true;
  }
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'T')
      runTests();
    else if (c == 'S')
      status();
    else if (c == 'F') {
      lv_obj_invalidate(lv_screen_active());
      lv_refr_now(lv_display_get_default());
      Serial.println("FRAME_BEGIN 320 170 RGB565_LE 108800");
      Serial.write(reinterpret_cast<uint8_t *>(frame), 108800);
      Serial.println("\nFRAME_END");
    } else if (c == 'R') {
      Serial.println("REBOOT");
      Serial.flush();
      ESP.restart();
    } else if (c == 'E')
      key(LV_KEY_ENTER);
    else if (c == 'N')
      key(LV_KEY_NEXT);
  }
  if (nextKey.raw != raw0 || enterKey.raw != raw14) {
    Serial.printf("PHYSICAL_RAW uptime=%lu next=%d enter=%d\n", millis(),
                  nextKey.raw, enterKey.raw);
    raw0 = nextKey.raw;
    raw14 = enterKey.raw;
  }
  if (nextKey.pressed != old0 || enterKey.pressed != old14) {
    Serial.printf("PHYSICAL_KEY uptime=%lu next=%d enter=%d count=%d\n",
                  millis(), nextKey.pressed, enterKey.pressed, count);
    old0 = nextKey.pressed;
    old14 = enterKey.pressed;
  }
  auto *focused = lv_group_get_focused(ui.group());
  if (count != oldCount || focused != oldFocus || millis() - last >= 10000) {
    status();
    oldCount = count;
    oldFocus = focused;
    last = millis();
  }
}
