#!/usr/bin/env python3
"""
Photo -> ASCII portrait -> self-typing SVG.

Usage:
    python3 portrait.py input.jpg portrait.svg --cols 90 --display-width 460

Pipeline (per the guide):
  1. background cutout (rembg, optional --no-cutout to skip)
  2. bilateral filter (smooth skin, keep edges)
  3. CLAHE local contrast
  4. darkening curve (v/255)^GAMMA  -- the fix for washed-out faces
  5. map to a 13-level ramp, leading space = background
  6. emit an SVG where each row wipes in via clipPath + SMIL, staggered
"""
import argparse
import base64
import sys

import cv2
import numpy as np
from PIL import Image

RAMP = " .`:-=+*cs#%@"  # 13 levels, light -> dark
GAMMA = 1.7
CHAR_W_EM = 0.600  # advance width baked into the grid; matches JetBrains Mono etc.
FONT_SIZE = 12.9
LINE_HEIGHT_EM = 1.0


def cutout(img_rgb: np.ndarray) -> np.ndarray:
    """Force background to white so it maps to the blank end of the ramp."""
    try:
        from rembg import remove
    except ImportError:
        print(
            "[portrait] rembg not installed — skipping background cutout.\n"
            "           Install with: pip install rembg onnxruntime --break-system-packages\n"
            "           (adds a ~176MB model download on first run)",
            file=sys.stderr,
        )
        return img_rgb

    pil = Image.fromarray(img_rgb)
    result = remove(pil)  # RGBA, transparent background
    arr = np.array(result)
    if arr.shape[-1] == 4:
        alpha = arr[:, :, 3:4] / 255.0
        white = np.ones_like(arr[:, :, :3]) * 255
        composited = (arr[:, :, :3] * alpha + white * (1 - alpha)).astype(np.uint8)
        return composited
    return arr[:, :, :3]


def process(img_path: str, cols: int, no_cutout: bool) -> str:
    img = cv2.imread(img_path)
    if img is None:
        raise SystemExit(f"could not read {img_path}")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if not no_cutout:
        img_rgb = cutout(img_rgb)

    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    # bilateral filter: smooth skin, keep edges
    smoothed = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # CLAHE local contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(smoothed)

    # darkening curve (v/255)^gamma -- keeps glasses/brows/lips from washing out
    curved = (np.power(contrasted / 255.0, GAMMA) * 255.0).astype(np.uint8)

    # resize to character grid; rows compensate for glyph aspect ratio (~2:1 tall)
    h, w = curved.shape
    rows = max(1, round(cols * (h / w) * 0.48))
    resized = cv2.resize(curved, (cols, rows), interpolation=cv2.INTER_AREA)

    ramp_len = len(RAMP)
    lines = []
    for r in range(rows):
        line = []
        for c in range(cols):
            v = int(resized[r, c])
            # bright pixel (v high) -> light end of ramp (space); dark -> '@'
            idx = min(ramp_len - 1, ((255 - v) * ramp_len) // 256)
            line.append(RAMP[idx])
        lines.append("".join(line))
    return "\n".join(lines)


def escape(ch: str) -> str:
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(ch, ch)


def build_svg(ascii_art: str, display_width: int, font_data_uri: str | None) -> str:
    lines = ascii_art.split("\n")
    cols = max(len(l) for l in lines)
    rows = len(lines)

    char_w = FONT_SIZE * CHAR_W_EM
    char_h = FONT_SIZE * LINE_HEIGHT_EM
    art_w = cols * char_w
    art_h = rows * char_h
    scale = display_width / art_w
    display_height = round(art_h * scale)

    font_face = ""
    if font_data_uri:
        font_face = f"""
    <style type="text/css"><![CDATA[
      @font-face {{
        font-family: 'RampMono';
        src: url('{font_data_uri}') format('woff2');
      }}
    ]]></style>"""

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {art_w:.1f} {art_h:.1f}" width="{display_width}" height="{display_height}" '
        f'role="img" aria-label="ASCII self-portrait">',
        font_face,
        f'  <rect width="{art_w:.1f}" height="{art_h:.1f}" fill="white"/>',
        f'  <g font-family="RampMono, monospace" font-size="{FONT_SIZE}" fill="#111">',
    ]

    row_delay = 0.09
    for i, line in enumerate(lines):
        y = (i + 1) * char_h - char_h * 0.22
        text = "".join(escape(c) for c in line) or " "
        clip_id = f"clip{i}"
        parts.append(f'    <clipPath id="{clip_id}">')
        parts.append(
            f'      <rect x="0" y="{i * char_h:.2f}" width="0" height="{char_h:.2f}">'
            f'<animate attributeName="width" from="0" to="{art_w:.1f}" '
            f'begin="{i * row_delay:.2f}s" dur="0.35s" fill="freeze"/>'
            f"</rect>"
        )
        parts.append(f"    </clipPath>")
        parts.append(f'    <g clip-path="url(#{clip_id})">')
        parts.append(f'      <text x="0" y="{y:.2f}" xml:space="preserve">{text}</text>')
        parts.append(f"    </g>")

    parts.append("  </g>")
    parts.append("</svg>")
    return "\n".join(p for p in parts if p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--cols", type=int, default=90)
    ap.add_argument("--display-width", type=int, default=460)
    ap.add_argument("--no-cutout", action="store_true")
    ap.add_argument("--font", help="path to a woff2 file to embed (base64)")
    args = ap.parse_args()

    ascii_art = process(args.input, args.cols, args.no_cutout)

    font_data_uri = None
    if args.font:
        with open(args.font, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        font_data_uri = f"data:font/woff2;base64,{b64}"

    svg = build_svg(ascii_art, args.display_width, font_data_uri)
    with open(args.output, "w") as f:
        f.write(svg)

    # also dump the raw ascii for inspection
    with open(args.output.replace(".svg", ".txt"), "w") as f:
        f.write(ascii_art)

    print(f"[portrait] {ascii_art.count(chr(10)) + 1} rows written -> {args.output}")


if __name__ == "__main__":
    main()
