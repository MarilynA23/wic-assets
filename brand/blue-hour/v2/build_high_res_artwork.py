# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy==2.5.4", "Pillow==13.0.0"]
# ///
"""Rebuild Blue Hour's decorative artwork at 4x, preserving its grain scale.

Run: uv run build_high_res_artwork.py

By default only studio-assets/hires/ is written. Header, body, date and fact
text are never rasterized. The approved 2x artwork is checked but never changed.
In the hosted repository's brand/blue-hour/v2 folder, reproduce these files with:
uv run build_high_res_artwork.py --reference-directory ../v1 --output-directory .

The smooth colour fields are recomputed at 4x. Grain uses the original seeded
2x lattice, with nearest-neighbour expansion of its *noise samples*, not of a
finished image. Each original grain sample occupies 2x2 output pixels. This
keeps its position, displayed size and contrast. Bilinear grain expansion would
blur it; generating new grain per 4x pixel would halve its apparent size.

Formula provenance: the original build_design_art.py and refine_gradient_art.py
from this design session, using the portfolio renderer's four-neighbour fleck
and bounded grain distribution. Geometry/overlays: design-assets/preview.css,
especially .blue-date:before and .newsletter .edition-colophon:before.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import PIL
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "studio-assets" / "hires"
REFERENCE_WIDTH = 1440  # 720 CSS pixels, at the approved 2x grain scale.
REFERENCE_HEIGHT = 1100
PAPER = (11, 16, 25)
PALETTE_TILES = {
    "ink-heading": "#25314b",
    "ink-body": "#26334d",
    "ink-caption": "#46587b",
    "ink-stamp": "#445579",
    "white": "#ffffff",
}


def colour(value: str) -> np.ndarray:
    return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=float)


def coordinates(width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:height, 0:width].astype(float)
    return x / width, y / height


def blend(image: np.ndarray, value: str, amount: np.ndarray) -> np.ndarray:
    amount = np.clip(amount, 0, 1)[..., None]
    return image * (1 - amount) + colour(value) * amount


def fleck(rng: np.random.Generator, width: int, height: int) -> np.ndarray:
    samples = rng.random((height + 1, width + 1))
    return (
        samples[:-1, :-1]
        + samples[1:, :-1]
        + samples[:-1, 1:]
        + samples[1:, 1:]
        - 2
    ) * np.sqrt(3)


def bounded_grain(values: np.ndarray) -> np.ndarray:
    t = np.tanh(0.52 * values)
    return (t - 0.215 * t * t + 0.040760815) / 0.434222832


def expand_noise(values: np.ndarray, factor: int) -> np.ndarray:
    return values if factor == 1 else values.repeat(factor, 0).repeat(factor, 1)


def rgb(image: np.ndarray) -> Image.Image:
    # Match the original builders' clipping and truncation exactly.
    return Image.fromarray(np.clip(image, 0, 255).astype("uint8"))


def header(factor: int) -> Image.Image:
    width, height = REFERENCE_WIDTH * factor, REFERENCE_HEIGHT * factor
    x, y = coordinates(width, height)

    def cloud(cx: float, cy: float, sx: float, sy: float) -> np.ndarray:
        return np.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2) / 2)

    image = np.broadcast_to(colour("080C15"), (height, width, 3)).copy()
    image = blend(image, "142A64", cloud(0.45, 0.54, 0.65, 0.24) * 0.9)
    image = blend(image, "2359CB", cloud(0.63, 0.65, 0.51, 0.14) * 0.95)
    ridge = 0.715 + 0.032 * np.sin(x * 5.2) - 0.065 * x
    band = np.exp(-((y - ridge) / 0.065) ** 2 / 2)
    image = blend(image, "9CBCE4", band * 0.82)
    image = blend(image, "869BBC", cloud(-0.1, 0.71, 0.49, 0.08) * 0.78)
    image = blend(image, "536E89", cloud(0.53, 0.86, 0.60, 0.10) * 0.9)
    image = blend(image, "1A3047", cloud(0.94, 0.89, 0.32, 0.10) * 0.9)
    image = blend(image, "080C15", np.clip((y - 0.88) / 0.12, 0, 1))

    density = np.clip((np.max(image, axis=2) - 18) / 90, 0, 1)
    density = 0.035 + 0.965 * density * density * (3 - 2 * density)
    sigma = (17 + 7 * np.clip(image[:, :, 1] / 90, 0, 1)) * density
    rng = np.random.default_rng(71)
    grain = expand_noise(bounded_grain(fleck(rng, 1440, 1100)), factor)
    primary = grain * sigma
    chroma1 = expand_noise(fleck(rng, 1440, 1100), factor) * sigma * 0.18
    chroma2 = expand_noise(fleck(rng, 1440, 1100), factor) * sigma * 0.10
    image += np.stack(
        (primary * 0.96 + chroma1, primary, primary * 0.98 + chroma1 * 0.4 + chroma2),
        axis=2,
    )
    return rgb(image)


def curiosity(factor: int) -> Image.Image:
    width, height = 1440 * factor, 640 * factor
    x, y = coordinates(width, height)
    position = np.clip(0.62 * x + 0.38 * y + 0.05 * np.sin(x * 4), 0, 1)
    image = np.zeros((height, width, 3), dtype=float)
    stops = (0, 0.5, 1)
    swatches = np.array([colour(v) for v in ("DDD6EC", "BDCBEB", "99B8DC")])
    for index in range(2):
        mask = (position >= stops[index]) & (position <= stops[index + 1])
        amount = np.clip(
            (position - stops[index]) / (stops[index + 1] - stops[index]), 0, 1
        )
        amount = amount * amount * (3 - 2 * amount)
        for channel in range(3):
            image[:, :, channel][mask] = (
                swatches[index, channel] * (1 - amount)
                + swatches[index + 1, channel] * amount
            )[mask]

    rng = np.random.default_rng(781)
    # The original builder first made field-notes, consuming two fleck fields.
    # Advance identically so the curiosity specks stay in their exact positions.
    for _ in range(2):
        rng.random((1101, 1441))
    grain = expand_noise(bounded_grain(fleck(rng, 1440, 640)), factor)
    chroma = expand_noise(fleck(rng, 1440, 640), factor) * 10.5 * 0.14
    image += np.stack(
        (grain * 10.5 * 0.96 + chroma, grain * 10.5, grain * 10.5 * 0.98 + chroma * 0.4),
        axis=2,
    )
    return rgb(image)


def background_crop(source: Image.Image, height: int, position: float) -> Image.Image:
    """CSS background-position, with fractional crop sampling only when needed."""
    top = (source.height - height) * position
    if top.is_integer():
        return source.crop((0, int(top), source.width, int(top) + height))
    return source.transform(
        (source.width, height),
        Image.Transform.EXTENT,
        (0, top, source.width, top + height),
        Image.Resampling.BILINEAR,
    )


def css_overlay(
    source: Image.Image,
    height: int,
    position: float,
    overlay_colour: tuple[int, int, int],
    alpha_start: int,
    alpha_end: int,
    base_colour: tuple[int, int, int],
) -> Image.Image:
    """Flatten a CSS linear alpha gradient, then pseudo-element opacity .8."""
    crop = background_crop(source, height, position)
    alphas = np.rint(
        alpha_start + (alpha_end - alpha_start) * ((np.arange(height) + 0.5) / height)
    ).astype("uint8")
    mask = Image.fromarray(np.broadcast_to(alphas[:, None], (height, source.width)).copy())
    overlay = Image.composite(Image.new("RGB", crop.size, overlay_colour), crop, mask)
    return Image.blend(Image.new("RGB", crop.size, base_colour), overlay, 0.8)


def differences(actual: Image.Image, reference: Image.Image) -> dict:
    a = np.asarray(actual.convert("RGB"), dtype=np.int16)
    b = np.asarray(reference.convert("RGB"), dtype=np.int16)
    delta = np.abs(a - b)
    return {
        "mean_absolute_channel_error": round(float(delta.mean()), 6),
        "max_channel_error": int(delta.max()),
        "identical_pixels_percent": round(float(np.all(delta == 0, axis=2).mean() * 100), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-directory", type=Path, default=ROOT / "design-assets")
    parser.add_argument("--output-directory", type=Path, default=OUT)
    args = parser.parse_args()
    reference_dir = args.reference_directory.resolve()
    output_dir = args.output_directory.resolve()
    # The hosted v1 folder retains its full original as curiosity-master.png;
    # the newsletter project calls that same full image curiosity.png.
    curiosity_reference = reference_dir / "curiosity-master.png"
    if not curiosity_reference.exists():
        curiosity_reference = reference_dir / "curiosity.png"
    # These checks prove the transcribed formula/RNG sequence reproduces the
    # approved masters exactly before producing any new deliverable files.
    originals = {
        "blue-hour": Image.open(reference_dir / "blue-hour.png").convert("RGB"),
        "curiosity": Image.open(curiosity_reference).convert("RGB"),
    }
    checks = {}
    for name, builder in (("blue-hour", header), ("curiosity", curiosity)):
        checks[name] = differences(builder(1), originals[name])
        if checks[name]["max_channel_error"] != 0:
            raise RuntimeError(f"Original {name} artwork does not match its seeded formula: {checks[name]}")

    output_dir.mkdir(parents=True, exist_ok=True)
    blue = header(2)
    fact = curiosity(2)
    outputs = {
        "blue-hour": blue,
        "curiosity": fact,
        "footer": css_overlay(blue, 1000, 0.60, (16, 23, 33), 166, 85, (12, 18, 29)),
        "date-tile": css_overlay(blue, 420, 0.52, (16, 26, 41), 163, 240, PAPER),
        "date-tile-mobile": css_overlay(blue, 396, 0.52, (16, 26, 41), 163, 240, PAPER),
    }
    report = {
        "schemaVersion": 1,
        "dependencies": {"numpy": np.__version__, "Pillow": PIL.__version__},
        "outputScale": 4,
        "grainScale": 2,
        "grainSampling": "Original seeded 2x noise lattice, nearest-neighbour expanded to 4x; smooth fields recomputed at 4x.",
        "referenceFormulaChecks": checks,
        "assets": {},
    }
    for name, image in outputs.items():
        path = output_dir / (name + ".png")
        image.save(path, optimize=True)
        data = path.read_bytes()
        entry = {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        if name in originals:
            entry["boxDownsampleComparedToApproved2x"] = differences(
                image.resize(originals[name].size, Image.Resampling.BOX), originals[name]
            )
            # Matching every top-left subpixel demonstrates an unchanged noise
            # lattice and colour field at the original sample coordinates.
            entry["originalSampleCoordinatesComparison"] = differences(
                Image.fromarray(np.asarray(image)[::2, ::2].copy()), originals[name]
            )
        report["assets"][path.name] = entry
        display_path = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        print(f"{display_path}: {image.width} x {image.height}, RGB, {len(data):,} bytes")
    for name, fill in PALETTE_TILES.items():
        path = output_dir / (name + ".svg")
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1" viewBox="0 0 1 1">'
            f'<rect width="1" height="1" fill="{fill}"/></svg>\n'
        )
        data = path.read_bytes()
        report["assets"][path.name] = {
            "width": 1, "height": 1, "mode": "SVG", "kind": "solid-palette-tile",
            "fill": fill, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }
    path = output_dir / "social-button.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">'
        '<rect x=".5" y=".5" width="43" height="43" rx="2.5" fill="#0c182a" '
        'fill-opacity=".321569" stroke="#c1d6f0" stroke-opacity=".301961" stroke-width="1"/></svg>\n'
    )
    data = path.read_bytes()
    report["assets"][path.name] = {
        "width": 44, "height": 44, "mode": "SVG", "kind": "social-button-background",
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    (output_dir / "README.txt").write_text(
        "Blue Hour decorative artwork, 4x\n\n"
        "Rebuild with: uv run build_high_res_artwork.py\n"
        "All files are full-colour, lossless RGB PNGs. No text is rasterized.\n"
        "Display blue-hour at 720x550 CSS px, curiosity at 720x320, footer at\n"
        "720x250, date-tile at 720x105, and date-tile-mobile at 720x99.\n\n"
        "The original seeded 2x grain lattice is retained. Smooth gradients are\n"
        "recomputed at 4x; grain samples use nearest-neighbour expansion so\n"
        "speck size, contrast and positions match the approved design. This\n"
        "does not invent extra grain detail or enlarge an existing bitmap.\n\n"
        "Footer: source background center 60%, linear #101721a6 to #10172155,\n"
        "80% opacity over #0c121d. Date backgrounds: center 52%, linear\n"
        "#101a29a3 to #101a29f0, 80% opacity over #0b1019. Borders stay HTML.\n"
        "The 4x files are larger than their 2x equivalents. Use the manifest to\n"
        "compare sizes and the exact source-pixel verification results.\n"
        "The five SVG files are simple solid palette rectangles for live-HTML\n"
        "compositing; they contain no text, scripts or external references.\n"
    )


if __name__ == "__main__":
    main()
