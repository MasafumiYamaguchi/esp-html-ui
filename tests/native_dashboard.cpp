#include "../examples/web-dashboard/src/DashboardDemo.h"
#include <array>
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>

namespace {
constexpr int Width = 320, Height = 170;
alignas(4) std::array<uint8_t, Width * 20 * 2> drawBuffer{};
std::array<uint16_t, Width * Height> frame{};

void flush(lv_display_t* display, const lv_area_t* area, uint8_t* pixels) {
  auto* source = reinterpret_cast<uint16_t*>(pixels);
  for (int y = area->y1; y <= area->y2; ++y) {
    for (int x = area->x1; x <= area->x2; ++x) frame[y * Width + x] = *source++;
  }
  lv_display_flush_ready(display);
}

void checkBounds(lv_obj_t* object) {
  lv_area_t area;
  lv_obj_get_coords(object, &area);
  if (area.x1 < 0 || area.y1 < 0 || area.x2 >= Width || area.y2 >= Height) {
    std::cerr << "Out of bounds: " << area.x1 << ',' << area.y1 << " - " << area.x2 << ',' << area.y2 << '\n';
    assert(false);
  }
  for (uint32_t i = 0; i < lv_obj_get_child_count(object); ++i) checkBounds(lv_obj_get_child(object, i));
}

void save(const char* path) {
  std::ofstream out(path, std::ios::binary);
  out << "P6\n" << Width << ' ' << Height << "\n255\n";
  for (uint16_t p : frame) {
    const uint8_t rgb[] = {static_cast<uint8_t>(((p >> 11) & 31) * 255 / 31),
                           static_cast<uint8_t>(((p >> 5) & 63) * 255 / 63),
                           static_cast<uint8_t>((p & 31) * 255 / 31)};
    out.write(reinterpret_cast<const char*>(rgb), 3);
  }
  assert(out.good());
}
void click(lv_obj_t* button) { lv_obj_send_event(button, LV_EVENT_CLICKED, nullptr); }
} // namespace

int main(int argc, char** argv) {
  lv_init();
  auto* display = lv_display_create(Width, Height);
  lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
  lv_display_set_flush_cb(display, flush);
  lv_display_set_buffers(display, drawBuffer.data(), nullptr, drawBuffer.size(), LV_DISPLAY_RENDER_MODE_PARTIAL);
  {
    DashboardDemo demo;
    assert(demo.begin(lv_screen_active()));
    auto& ui = demo.ui();
    assert(lv_group_get_obj_count(ui.group()) == 2);
    assert(lv_group_get_focused(ui.group()) == ui.find("refresh"));
    lv_obj_update_layout(ui.root());
    checkBounds(ui.root());
    assert(lv_obj_get_height(ui.find("logo")) <= 24);
    assert(lv_obj_get_height(ui.find("breadcrumb")) <= 24);
    lv_refr_now(display);
    assert(frame[0] == lv_color_to_u16(lv_color_hex(0x0f172a)));
    assert(frame[169 * Width] == 0xffff);
    if (argc > 1) save(argv[1]);

    demo.tick(1999);
    assert(demo.requests() == 1284);
    demo.tick(2000);
    assert(demo.requests() == 1301);
    assert(std::strcmp(lv_label_get_text(ui.find("requests")), "1,301") == 0);
    lv_group_focus_next(ui.group());
    assert(lv_group_get_focused(ui.group()) == ui.find("pause"));
    click(ui.find("pause"));
    assert(!demo.automatic());
    assert(std::strcmp(lv_label_get_text(lv_obj_get_child(ui.find("pause"), 0)), "Resume") == 0);
    demo.tick(20000);
    assert(demo.requests() == 1301);
    click(ui.find("refresh"));
    assert(demo.requests() == 1319);
    click(ui.find("pause"));
    assert(demo.automatic());
    demo.tick(21999);
    assert(demo.requests() == 1319);
    demo.tick(22000);
    assert(demo.requests() == 1338);
    lv_obj_update_layout(ui.root());
    checkBounds(ui.root());
    lv_refr_now(display);
  }
  lv_display_delete(display);
  lv_deinit();
  std::cout << "Dashboard render, all widget bounds, timed updates, refresh, pause/resume and focus OK\n";
}
