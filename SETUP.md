# Setup

1. Rename this repo to your exact GitHub username (a "profile README" repo —
   GitHub only renders this special README on your profile page if the repo
   name matches your username exactly, public, with a README.md at the root).

2. Regenerate the four heading SVGs with your own font choice if you want
   (JetBrains Mono is bundled under OFL in assets/fonts/ — keep the LICENSE
   file alongside it if you ship a different OFL font):

   python3 scripts/heading.py "about" assets/heading_about.svg --font assets/fonts/JetBrainsMono-Regular.ttf

3. Edit README.md — swap in your real project list and contact links.

4. Commit and push. The refresh.yml workflow needs no secrets beyond the
   built-in GITHUB_TOKEN; it runs nightly at 05:17 UTC and on manual dispatch,
   and only commits stats.svg/streak.svg/langs.svg/year.svg when they've
   actually changed.

5. Pinned repos and your bio are NOT settable via API — set those once by
   hand in the GitHub UI.

## What was verified while building this

- Font subset: measured advance width came out to exactly 0.600em against
  JetBrains Mono — matters if you regenerate other SVGs with the same font
  and want consistent character-grid math.
- Stats SVGs: the four builder functions in generate_stats.py were
  unit-tested against synthetic contribution/language data (no live token
  in the build environment) and rasterize cleanly.
- README sanitizer compliance: the actual README.md in this folder was
  POSTed to GitHub's own `api.github.com/markdown` endpoint. img/width,
  blockquote, table, samp, sub, and hr all survive untouched, confirming
  the template renders as designed on a real profile page.
- Not tested live: the GraphQL contributions query itself needs a real
  token, so you'll want to sanity-check the first automated run.
