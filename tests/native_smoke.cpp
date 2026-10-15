#include <EspHtmlUi.h>
#include "counter.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>

namespace {
constexpr int Width = 320, Height = 170;
alignas(4) std::array<uint8_t, Width * 20 * 2> drawBuffer{};
std::array<uint16_t, Width * Height> frame{};

void flush(lv_display_t* display, const lv_area_t* area, uint8_t* pixels) {
  const auto* source = reinterpret_cast<const uint16_t*>(pixels);
  for (int y = area->y1; y <= area->y2; ++y) {
    for (int x = area->x1; x <= area->x2; ++x) frame[y * Width + x] = *source++;
  }
  lv_display_flush_ready(display);
}

void clicked(lv_event_t* event) { ++*static_cast<int*>(lv_event_get_user_data(event)); }

void saveFrame(const char* path) {
  std::ofstream output(path, std::ios::binary);
  output << "P6\n" << Width << ' ' << Height << "\n255\n";
  for (uint16_t pixel : frame) {
    const uint8_t rgb[] = {
      static_cast<uint8_t>(((pixel >> 11) & 31) * 255 / 31),
      static_cast<uint8_t>(((pixel >> 5) & 63) * 255 / 63),
      static_cast<uint8_t>((pixel & 31) * 255 / 31)
    };
    output.write(reinterpret_cast<const char*>(rgb), 3);
  }
  assert(output.good());
}
} // namespace

int main(int argc, char** argv) {
  lv_init();
  auto* display = lv_display_create(Width, Height);
  lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
  lv_display_set_buffers(display, drawBuffer.data(), nullptr, drawBuffer.size(), LV_DISPLAY_RENDER_MODE_PARTIAL);
  lv_display_set_flush_cb(display, flush);
  {
    esphtml::generated::counter::Ui ui;
    auto* parent = lv_obj_create(lv_screen_active());
    lv_obj_remove_style_all(parent);
    lv_obj_set_size(parent, Width, Height);
    assert(ui.create(parent));
    assert(ui.find("increment") && ui.find("reset") && ui.find("value"));
    assert(!ui.find("missing") && !ui.find(nullptr));
    assert(lv_group_get_obj_count(ui.group()) == 2);
    assert(ui.focus("increment"));
    lv_obj_update_layout(parent);

    // Generated layout must fit the intended display and contain usable buttons.
    for (const char* id : {"value", "increment", "reset"}) {
      lv_area_t area;
      lv_obj_get_coords(ui.find(id), &area);
      assert(area.x1 >= 0 && area.y1 >= 0 && area.x2 < Width && area.y2 < Height);
    }
    assert(lv_obj_get_width(ui.find("increment")) >= 100);
    assert(lv_obj_get_height(ui.find("increment")) == 36);
    lv_refr_now(display);
    assert(frame[0] == lv_color_to_u16(lv_color_hex(0x0f172a)));
    if (argc > 1) saveFrame(argv[1]);

    assert(ui.setText("value", "123"));
    assert(std::strcmp(lv_label_get_text(ui.find("value")), "123") == 0);
    assert(ui.setText("increment", "Add"));
    assert(ui.setText("increment", "A much longer button caption that needs wrapping"));
    lv_obj_update_layout(parent);
    assert(lv_obj_get_width(lv_obj_get_child(ui.find("increment"), 0)) <= lv_obj_get_content_width(ui.find("increment")));
    assert(!ui.setText("missing", "X") && !ui.setText("value", nullptr));
    int clicks = 0;
    assert(ui.onClick("increment", clicked, &clicks));
    lv_obj_send_event(ui.find("increment"), LV_EVENT_CLICKED, nullptr);
    assert(clicks == 1);
    assert(!ui.onClick("value", clicked, &clicks));
    assert(ui.setDisabled("reset", true));
    assert(!ui.focus("reset"));
    lv_group_focus_next(ui.group());
    assert(lv_group_get_focused(ui.group()) == ui.find("increment"));
    assert(ui.setDisabled("reset", false));
    assert(ui.focus("reset"));
    assert(ui.setHidden("reset", true));
    assert(!ui.focus("reset"));
    assert(ui.setHidden("reset", false));

    // External child/parent deletion must invalidate IDs before they can be reused.
    lv_obj_delete(ui.find("value"));
    assert(!ui.find("value") && !ui.setText("value", "stale"));
    assert(ui.root() && ui.find("increment"));
    lv_obj_delete(parent);
    assert(!ui.root() && !ui.find("increment"));
    assert(!ui.setText("increment", "stale"));
    ui.clear();

    assert(ui.create(lv_screen_active()));
    ui.clear();
    lv_mem_monitor_t before, after;
    lv_mem_monitor(&before);
    for (int i = 0; i < 100; ++i) {
      assert(ui.create(lv_screen_active()));
      ui.clear();
    }
    lv_mem_monitor(&after);
    assert(after.free_size == before.free_size);
  }
  lv_display_delete(display);
  lv_deinit();
  std::cout << "Native LVGL render, layout, events, focus, lifetime and 100 create/clear cycles OK\n";
}
