# Setup

1. Rename this repo to your exact GitHub username (a "profile README" repo — GitHub
   only renders this special README on your profile page if the repo name matches
   your username exactly, public, with a README.md at the root).

2. Drop a headshot at `raw/me.jpg` — side-lit ~45°, tight crop chin-to-hairline,
   1200px+, plain background. Then:

   pip install pillow numpy opencv-python-headless --break-system-packages
   # optional but recommended, for a clean cutout instead of --no-cutout:
   pip install rembg onnxruntime --break-system-packages   # ~176MB model, once

   python3 scripts/portrait.py raw/me.jpg assets/portrait.svg \
       --cols 90 --display-width 460 --font assets/fonts/ramp.woff2

3. Regenerate the four heading SVGs with your own font choice if you want
   (JetBrains Mono is bundled under OFL in assets/fonts/ — keep the LICENSE
   file alongside it if you ship a different OFL font):

   python3 scripts/heading.py "about" assets/heading_about.svg --font assets/fonts/JetBrainsMono-Regular.ttf

4. Edit README.md — swap in your real project list and contact links.

5. Commit and push. The refresh.yml workflow needs no secrets beyond the
   built-in GITHUB_TOKEN; it runs nightly at 05:17 UTC and on manual dispatch,
   and only commits stats.svg/streak.svg/langs.svg/year.svg when they've
   actually changed.

6. Pinned repos and your bio are NOT settable via API — set those once by
   hand in the GitHub UI.

## What was verified while building this (see build notes)

- Portrait pipeline: fixed an inverted brightness->ramp mapping (white
  background was rendering as solid black) via a synthetic test image, since
  no real photo was available.
- Font subset: measured advance width came out to exactly 0.600em against
  JetBrains Mono, matching the grid math in portrait.py — no glyph drift.
- Stats SVGs: the four builder functions were unit-tested against synthetic
  contribution/language data (no live token in this environment) and
  rasterize cleanly.
- README sanitizer compliance: the actual README.md in this folder was
  POSTed to GitHub's own `api.github.com/markdown` endpoint. img/width,
  blockquote, table, samp, sub, and hr all survive untouched, confirming
  the template renders as designed on a real profile page.
- Not tested live: the GraphQL contributions query itself (needs a real
  token) and the rembg cutout stage (needs the ~176MB model + your photo).
  Both are wired up and should work as written, but you'll want to sanity
  check the first automated run.
