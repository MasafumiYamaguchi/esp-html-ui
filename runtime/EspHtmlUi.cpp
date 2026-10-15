#include "EspHtmlUi.h"
#include <cstring>

namespace esphtml {

Screen::~Screen() { clear(); }

bool Screen::begin(lv_obj_t* parent, size_t count) {
  clear();
  if (!parent || count == 0) return false;
  elements_.resize(count);
  root_ = lv_obj_create(parent);
  if (!root_) { elements_.clear(); return false; }
  lv_obj_add_event_cb(root_, rootDeleted, LV_EVENT_DELETE, this);
  group_ = lv_group_create();
  if (!group_) { clear(); return false; }
  lv_group_set_wrap(group_, true);
  return true;
}

void Screen::bind(size_t index, const char* id, lv_obj_t* object, lv_obj_t* text, bool focusable) {
  auto& entry = elements_[index];
  entry.id = id;
  entry.object = object;
  entry.text = text;
  lv_obj_add_event_cb(object, elementDeleted, LV_EVENT_DELETE, &entry);
  if (focusable) lv_group_add_obj(group_, object);
}

const Screen::Element* Screen::element(const char* id) const {
  if (!id || !*id || !root_) return nullptr;
  for (const auto& entry : elements_) {
    if (entry.id && entry.object && std::strcmp(entry.id, id) == 0) return &entry;
  }
  return nullptr;
}

lv_obj_t* Screen::find(const char* id) const {
  const auto* entry = element(id);
  return entry ? entry->object : nullptr;
}

bool Screen::setText(const char* id, const char* text) {
  const auto* entry = element(id);
  if (!entry || !entry->text || !text) return false;
  lv_label_set_text(entry->text, text);
  return true;
}

bool Screen::setHidden(const char* id, bool hidden) {
  auto* object = find(id);
  if (!object) return false;
  if (hidden) lv_obj_add_flag(object, LV_OBJ_FLAG_HIDDEN);
  else lv_obj_remove_flag(object, LV_OBJ_FLAG_HIDDEN);
  return true;
}

bool Screen::setDisabled(const char* id, bool disabled) {
  auto* object = find(id);
  if (!object) return false;
  if (disabled) lv_obj_add_state(object, LV_STATE_DISABLED);
  else lv_obj_remove_state(object, LV_STATE_DISABLED);
  return true;
}

bool Screen::focus(const char* id) {
  auto* object = find(id);
  if (!object || lv_obj_get_group(object) != group_ ||
      !lv_obj_is_visible(object) || lv_obj_has_state(object, LV_STATE_DISABLED)) return false;
  lv_group_focus_obj(object);
  return true;
}

bool Screen::onClick(const char* id, lv_event_cb_t callback, void* userData) {
  auto* object = find(id);
  if (!object || !callback || !lv_obj_has_flag(object, LV_OBJ_FLAG_CLICKABLE)) return false;
  return lv_obj_add_event_cb(object, callback, LV_EVENT_CLICKED, userData) != nullptr;
}

void Screen::rootDeleted(lv_event_t* event) {
  auto* self = static_cast<Screen*>(lv_event_get_user_data(event));
  self->root_ = nullptr;
  for (auto& entry : self->elements_) { entry.object = nullptr; entry.text = nullptr; }
  if (self->group_) lv_group_remove_all_objs(self->group_);
}

void Screen::elementDeleted(lv_event_t* event) {
  auto* entry = static_cast<Element*>(lv_event_get_user_data(event));
  entry->object = nullptr;
  entry->text = nullptr;
}

void Screen::clear() {
  if (root_) lv_obj_delete(root_);
  if (group_) { lv_group_delete(group_); group_ = nullptr; }
  elements_.clear();
}

} // namespace esphtml
