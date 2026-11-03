# Blue Hour artwork, version 2

Four-times-resolution decorative backgrounds for the WiC newsletter. All newsletter text, including the header, dates and fact card, stays in HTML. Version 1 remains available unchanged.

| File | Pixel size | CSS background size |
| --- | --- | --- |
| blue-hour.png | 2880 × 2200 | 720 × 550 |
| curiosity.png | 2880 × 1280 | 720 × 320 |
| footer.png | 2880 × 1000 | 720 × 250 |
| date-tile.png | 2880 × 420 | 720 × 105 |
| date-tile-mobile.png | 2880 × 396 | 720 × 99 |

Every file is full-color, lossless RGB PNG. The original seeded grain lattice retains its visible size, contrast and positions. Smooth color fields are calculated at 4×, while each original 2× grain sample occupies 2 × 2 output pixels. This preserves the established grain instead of blurring it or making it finer. These files do not invent additional grain detail.

The footer uses the reference design's 60% background crop, vertical `#101721a6` to `#10172155` overlay, and 80% opacity over `#0c121d`. Date backgrounds use the 52% crop, `#101a29a3` to `#101a29f0`, and 80% opacity over `#0b1019`. Their borders and numerals stay HTML.

## Rebuild

From this folder, with uv installed:

```sh
uv run build_high_res_artwork.py --reference-directory ../v1 --output-directory .
```

The script pins NumPy and Pillow, verifies the original header and full fact artwork pixel-for-pixel before writing, and produces a manifest of image sizes, hashes and comparison results. `curiosity.png` here is the full 320-CSS-pixel field, corresponding to v1's `curiosity-master.png`, not v1's shorter crop. The shared glass overlay, navy paper tile and social icons remain in v1.

The header's 4× artwork sampled at the original coordinates matches every original pixel. Averaging back to 2× differs by at most 1/255 per channel; the fact artwork averages back exactly. The footer is recomposited in full RGB rather than carrying forward v1's indexed palette.

## Palette tiles

The 1 × 1 SVG files `ink-heading.svg`, `ink-body.svg`, `ink-caption.svg`, `ink-stamp.svg` and `white.svg` contain a single solid rectangle. They provide exact palette colors for HTML compositing without rasterizing text. Their colors and hashes are listed in the manifest. They contain no scripts or external references.
