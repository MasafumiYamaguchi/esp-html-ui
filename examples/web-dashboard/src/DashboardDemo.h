#pragma once

#include "dashboard.h"
#include <cstdint>

// Deterministic demo data, not network traffic or sensor measurements.
class DashboardDemo {
 public:
  bool begin(lv_obj_t* parent);
  void tick(uint32_t now);

  esphtml::generated::dashboard::Ui& ui();
  bool automatic() const;
  uint32_t requests() const;

 private:
  static void refreshClicked(lv_event_t* event);
  static void pauseClicked(lv_event_t* event);
  void refresh();

  esphtml::generated::dashboard::Ui ui_;
  uint32_t requests_ = 1284, sequence_ = 0, now_ = 0, lastUpdate_ = 0;
  bool automatic_ = true;
};
