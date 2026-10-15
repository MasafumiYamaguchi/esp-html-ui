#pragma once

#include <lvgl.h>
#include <cstddef>
#include <vector>

namespace esphtml {

// All methods run on the same task as lv_timer_handler().
// Parent deletion invalidates the UI automatically. Clear before lv_deinit().
class Screen {
 public:
  Screen() = default;
  virtual ~Screen();
  Screen(const Screen&) = delete;
  Screen& operator=(const Screen&) = delete;
  Screen(Screen&&) = delete;
  Screen& operator=(Screen&&) = delete;

  lv_obj_t* root() const { return root_; }
  lv_group_t* group() const { return group_; }
  lv_obj_t* find(const char* id) const;
  bool setText(const char* id, const char* text);
  bool setHidden(const char* id, bool hidden);
  bool setDisabled(const char* id, bool disabled);
  bool focus(const char* id);
  bool onClick(const char* id, lv_event_cb_t callback, void* userData = nullptr);
  void clear();

 protected:
  bool begin(lv_obj_t* parent, size_t count);
  void bind(size_t index, const char* id, lv_obj_t* object, lv_obj_t* text, bool focusable);

 private:
  struct Element {
    const char* id = nullptr;
    lv_obj_t* object = nullptr;
    lv_obj_t* text = nullptr;
  };
  const Element* element(const char* id) const;
  static void rootDeleted(lv_event_t* event);
  static void elementDeleted(lv_event_t* event);
  lv_obj_t* root_ = nullptr;
  lv_group_t* group_ = nullptr;
  std::vector<Element> elements_;
};

} // namespace esphtml
