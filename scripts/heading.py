#!/usr/bin/env python3
"""
Lowercase mono section heading as SVG: label + hairline rule to the right edge.
Embeds a font subset covering only the characters actually used, base64 data URI
(the only way custom type survives GitHub's README sanitizer / img-tag loading).

Usage: python3 heading.py "about" heading_about.svg --font assets/fonts/JetBrainsMono-Regular.ttf --width 640
"""
import argparse
import base64
import subprocess
import sys
import tempfile
from pathlib import Path

FONT_SIZE = 15
HEIGHT = 30


def subset_font(font_path: str, text: str) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        txt_file = Path(td) / "chars.txt"
        txt_file.write_text(text)
        out_file = Path(td) / "sub.woff2"
        subprocess.run(
            [
                "pyftsubset", font_path,
                f"--text-file={txt_file}",
                "--flavor=woff2",
                "--no-hinting",
                f"--output-file={out_file}",
            ],
            check=True,
            capture_output=True,
        )
        return out_file.read_bytes()


def build(label: str, width: int, font_path: str) -> str:
    unique_chars = "".join(sorted(set(label))) + " "
    font_bytes = subset_font(font_path, unique_chars)
    b64 = base64.b64encode(font_bytes).decode()

    label_w = len(label) * FONT_SIZE * 0.6
    rule_x = label_w + 14
    esc = label.replace("&", "&amp;").replace("<", "&lt;")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{HEIGHT}" viewBox="0 0 {width} {HEIGHT}" role="img" aria-label="{esc}">
  <style type="text/css"><![CDATA[
    @font-face {{ font-family: 'HeadFont'; src: url('data:font/woff2;base64,{b64}') format('woff2'); }}
  ]]></style>
  <text x="0" y="20" font-family="HeadFont, monospace" font-size="{FONT_SIZE}" fill="#111">{esc}</text>
  <line x1="{rule_x:.1f}" y1="15" x2="{width - 2}" y2="15" stroke="#ccc" stroke-width="1"/>
</svg>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("output")
    ap.add_argument("--font", required=True)
    ap.add_argument("--width", type=int, default=640)
    args = ap.parse_args()
    svg = build(args.label, args.width, args.font)
    Path(args.output).write_text(svg)
    print(f"[heading] wrote {args.output} ({len(svg)} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
