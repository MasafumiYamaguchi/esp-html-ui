#include "oled.h"
#include "../examples/ssd1306/src/ssd1306_buffer.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>

namespace {
using Ui = esphtml::generated::oled::Ui;
constexpr int Width = 128, Height = 64, FrameBytes = Width * Height / 8;
alignas(4) std::array<uint8_t, Width * Height> drawBuffer{};
std::array<uint8_t, FrameBytes> frame{}, pages{};
int flushes = 0;

void flush(lv_display_t* display, const lv_area_t* area, uint8_t* pixels) {
  assert(area->x1 == 0 && area->y1 == 0 && area->x2 == Width - 1 && area->y2 == Height - 1);
  esphtml::ssd1306::copyFrame<Width, Height>(pixels, pages.data());
  frame.fill(0);
  // Check every output bit against the source luminance at the same coordinate.
  for (int y = 0; y < Height; ++y) {
    for (int x = 0; x < Width; ++x) {
      const bool source = pixels[y * Width + x] >= 128;
      const bool target = (pages[(y / 8) * Width + x] >> (y % 8)) & 1;
      assert(source == target);
      if (target) frame[y * Width / 8 + x / 8] |= 0x80 >> (x % 8);
    }
  }
  ++flushes;
  lv_display_flush_ready(display);
}

void checkPageMapping() {
  std::array<uint8_t, Width * Height> input{};
  std::array<uint8_t, FrameBytes> output{};
  input[0] = 255;                       // (0, 0)
  input[127] = 128;                     // (127, 0), threshold inclusive
  input[7 * Width + 1] = 255;           // (1, 7)
  input[8 * Width + 2] = 255;           // (2, 8)
  input[63 * Width + 127] = 255;        // (127, 63)
  input[5] = 127;                       // Below threshold, stays black.
  esphtml::ssd1306::copyFrame<Width, Height>(input.data(), output.data());
  assert(output[0] == 1 && output[127] == 1 && output[1] == 128);
  assert(output[Width + 2] == 1 && output[FrameBytes - 1] == 128);
  assert(std::count_if(output.begin(), output.end(), [](uint8_t v) { return v != 0; }) == 5);
  input.fill(0);
  esphtml::ssd1306::copyFrame<Width, Height>(input.data(), output.data());
  assert(std::all_of(output.begin(), output.end(), [](uint8_t v) { return v == 0; }));
}

void clicked(lv_event_t* event) { ++*static_cast<int*>(lv_event_get_user_data(event)); }
} // namespace

int main(int argc, char** argv) {
  checkPageMapping();
  lv_init();
  auto* display = lv_display_create(Width, Height);
  lv_display_set_color_format(display, LV_COLOR_FORMAT_L8);
  lv_display_set_buffers(display, drawBuffer.data(), nullptr, drawBuffer.size(), LV_DISPLAY_RENDER_MODE_FULL);
  lv_display_set_flush_cb(display, flush);
  {
    Ui ui;
    assert(Ui::width() == Width && Ui::height() == Height);
    assert(ui.create(lv_screen_active()));
    for (const char* id : {"increment", "reset"}) {
      lv_obj_set_style_bg_color(ui.find(id), lv_color_white(), LV_STATE_FOCUSED);
      lv_obj_set_style_text_color(ui.find(id), lv_color_black(), LV_STATE_FOCUSED);
    }
    assert(ui.focus("increment"));
    lv_obj_update_layout(ui.root());
    for (const char* id : {"value", "increment", "reset"}) {
      lv_area_t area;
      lv_obj_get_coords(ui.find(id), &area);
      assert(area.x1 >= 0 && area.y1 >= 0 && area.x2 < Width && area.y2 < Height);
    }
    lv_refr_now(display);
    assert(flushes > 0);
    assert(std::any_of(frame.begin(), frame.end(), [](uint8_t p) { return p != 0; }));
    assert(std::any_of(frame.begin(), frame.end(), [](uint8_t p) { return p != 255; }));
    // This fixed title previously rendered only sparse fragments via LVGL 9.4 I1.
    // Require enough glyph coverage to catch that failure, beyond a nonblank frame.
    int titlePixels = 0;
    for (int y = 0; y < 18; ++y) {
      for (int x = 0; x < Width; ++x) {
        if (frame[y * Width / 8 + x / 8] & (0x80 >> (x % 8))) ++titlePixels;
      }
    }
    assert(titlePixels > 150);
    if (argc > 1) {
      std::ofstream out(argv[1], std::ios::binary);
      out << "P4\n" << Width << ' ' << Height << '\n';
      // PBM uses 1 for black, whereas SSD1306 uses 1 for a lit pixel.
      for (uint8_t pixel : frame) out.put(static_cast<char>(pixel ^ 0xff));
      assert(out.good());
    }
    const auto initial = frame;
    assert(ui.setText("value", "999999"));
    lv_refr_now(display);
    assert(frame != initial);
    assert(std::strcmp(lv_label_get_text(ui.find("value")), "999999") == 0);
    int clicks = 0;
    assert(ui.onClick("increment", clicked, &clicks));
    lv_obj_send_event(ui.find("increment"), LV_EVENT_CLICKED, nullptr);
    assert(clicks == 1);
    lv_group_focus_next(ui.group());
    assert(lv_group_get_focused(ui.group()) == ui.find("reset"));
  }
  lv_display_delete(display);
  lv_deinit();
  std::cout << "SSD1306 L8 render, 128x64 layout, threshold/page mapping, updates, events and focus OK\n";
}
