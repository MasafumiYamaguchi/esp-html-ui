#include "DashboardDemo.h"
#include <cstdio>
#include <initializer_list>

bool DashboardDemo::begin(lv_obj_t* parent) {
  if (!ui_.create(parent)) return false;
  ui_.onClick("refresh", refreshClicked, this);
  ui_.onClick("pause", pauseClicked, this);
  for (const char* id : {"refresh", "pause"}) {
    auto* button = ui_.find(id);
    lv_obj_set_style_outline_width(button, 2, LV_STATE_FOCUS_KEY);
    lv_obj_set_style_outline_pad(button, 1, LV_STATE_FOCUS_KEY);
    lv_obj_set_style_outline_color(button, lv_color_hex(0x2563eb), LV_STATE_FOCUS_KEY);
    lv_obj_set_style_bg_color(button, lv_color_hex(0x1d4ed8), LV_STATE_PRESSED);
    lv_obj_set_style_text_color(button, lv_color_white(), LV_STATE_PRESSED);
  }
  return ui_.focus("refresh");
}

void DashboardDemo::tick(uint32_t now) {
  now_ = now;
  if (automatic_ && now - lastUpdate_ >= 2000) refresh();
}

esphtml::generated::dashboard::Ui& DashboardDemo::ui() { return ui_; }
bool DashboardDemo::automatic() const { return automatic_; }
uint32_t DashboardDemo::requests() const { return requests_; }

void DashboardDemo::refreshClicked(lv_event_t* event) {
  static_cast<DashboardDemo*>(lv_event_get_user_data(event))->refresh();
}

void DashboardDemo::pauseClicked(lv_event_t* event) {
  auto* self = static_cast<DashboardDemo*>(lv_event_get_user_data(event));
  self->automatic_ = !self->automatic_;
  self->lastUpdate_ = self->now_;
  self->ui_.setText("pause", self->automatic_ ? "Pause" : "Resume");
  self->ui_.setText("mode", self->automatic_ ? "AUTO / 2s" : "PAUSED");
}

void DashboardDemo::refresh() {
  requests_ += 17 + sequence_ % 7;
  if (requests_ > 9999) requests_ = 1200;
  ++sequence_;
  char text[16];
  std::snprintf(text, sizeof(text), "%lu,%03lu", static_cast<unsigned long>(requests_ / 1000),
                static_cast<unsigned long>(requests_ % 1000));
  ui_.setText("requests", text);
  std::snprintf(text, sizeof(text), "%lu", static_cast<unsigned long>(24 + sequence_ % 19));
  ui_.setText("latency", text);
  lastUpdate_ = now_;
}
