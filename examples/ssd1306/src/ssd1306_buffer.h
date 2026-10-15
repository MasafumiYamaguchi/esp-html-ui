#pragma once

#include <cstdint>
#include <cstring>

namespace esphtml {
namespace ssd1306 {

// LVGL L8: one luminance byte per pixel, row-major, with no palette.
// SSD1306: page-major bytes, with each byte holding 8 vertical LSB-first pixels.
// Render in L8 so antialiased font coverage is blended before thresholding.
template <uint32_t Width, uint32_t Height>
void copyFrame(const uint8_t* lvglPixels, uint8_t* pages) {
  static_assert(Width % 8 == 0 && Height % 8 == 0, "Use complete 8-pixel pages");
  std::memset(pages, 0, Width * Height / 8);
  for (uint32_t y = 0; y < Height; ++y) {
    for (uint32_t x = 0; x < Width; ++x) {
      if (lvglPixels[y * Width + x] >= 128) {
        pages[(y / 8) * Width + x] |= static_cast<uint8_t>(1U << (y % 8));
      }
    }
  }
}

} // namespace ssd1306
} // namespace esphtml
