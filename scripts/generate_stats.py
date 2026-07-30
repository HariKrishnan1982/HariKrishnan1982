#!/usr/bin/env python3
"""
Pull contribution + language data from the GitHub GraphQL API and draw
stats.svg / streak.svg / langs.svg / year.svg — no third-party services,
stdlib only (urllib), so nothing to break in CI.

Env vars required:
  GITHUB_TOKEN   -- provided automatically inside Actions
  GH_LOGIN       -- github.repository_owner
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

API_URL = "https://api.github.com/graphql"
RAMP = " .`:-=+*cs#%@"  # same ramp as the portrait, for the year strip

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
    repositories(first: 100, isFork: false, privacy: PUBLIC,
                 ownerAffiliations: OWNER) {
      nodes {
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def gh_graphql(query: str, variables: dict) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-stats",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def utc_window():
    """Whole-UTC-day window so two runs minutes apart bucket identically."""
    today = datetime.now(timezone.utc).date()
    to_dt = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
    from_dt = to_dt - timedelta(days=364, hours=23, minutes=59, seconds=59)
    return from_dt.isoformat(), to_dt.isoformat()


def svg_shell(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ui-monospace, monospace">\n'
        f'<rect width="{width}" height="{height}" fill="white"/>\n{body}\n</svg>'
    )


def build_stats_svg(days: list) -> str:
    total = sum(d["contributionCount"] for d in days)
    last_8w = days[-56:]
    weekly = [sum(w["contributionCount"] for w in last_8w[i:i + 7]) for i in range(0, len(last_8w), 7)]
    max_w = max(weekly) if weekly else 1
    bar_w, gap, base_h = 18, 6, 90
    body = [f'<text x="10" y="26" font-size="20" fill="#111">{total} contributions (last year)</text>']
    x = 10
    for w in weekly:
        h = 0 if max_w == 0 else round((w / max_w) * base_h)
        body.append(f'<rect x="{x}" y="{110 - h}" width="{bar_w}" height="{h}" fill="#00b34d"/>')
        x += bar_w + gap
    return svg_shell(x, 130, "\n".join(body))


def build_streak_svg(days: list) -> str:
    cur = longest = 0
    cur_start = longest_start = longest_end = None
    running_start = None
    for d in days:
        if d["contributionCount"] > 0:
            if running_start is None:
                running_start = d["date"]
            cur += 1
            if cur > longest:
                longest, longest_start, longest_end = cur, running_start, d["date"]
        else:
            cur, running_start = 0, None
    trailing = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            trailing += 1
        else:
            break
    body = [
        f'<text x="10" y="26" font-size="18" fill="#111">current streak: {trailing} days</text>',
        f'<text x="10" y="52" font-size="18" fill="#111">longest streak: {longest} days'
        + (f" ({longest_start} to {longest_end})" if longest_start else "") + "</text>",
    ]
    return svg_shell(420, 70, "\n".join(body))


def build_langs_svg(repos: list) -> str:
    totals: dict[str, int] = {}
    colors: dict[str, str] = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or "#888"
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    grand = sum(v for _, v in ranked) or 1
    body = []
    y = 26
    for name, size in ranked:
        pct = size / grand * 100
        body.append(f'<circle cx="16" cy="{y - 5}" r="5" fill="{colors[name]}"/>')
        body.append(f'<text x="30" y="{y}" font-size="14" fill="#111">{name} — {pct:.1f}%</text>')
        y += 22
    return svg_shell(260, y, "\n".join(body))


def build_year_svg(days: list) -> str:
    counts = [d["contributionCount"] for d in days]
    max_c = max(counts) if counts else 1
    body = []
    for i, c in enumerate(counts):
        idx = 0 if max_c == 0 else min(len(RAMP) - 1, round((c / max_c) * (len(RAMP) - 1)))
        ch = RAMP[idx].replace("&", "&amp;").replace("<", "&lt;")
        col, row = divmod(i, 26)
        x, y = 10 + col * 13, 20 + row * 15
        body.append(f'<text x="{x}" y="{y}" font-size="13">{ch}</text>')
    cols = (len(counts) // 26) + 1
    return svg_shell(20 + cols * 13, 20 + 26 * 15, "\n".join(body))


def main():
    login = os.environ["GH_LOGIN"]
    from_iso, to_iso = utc_window()
    data = gh_graphql(QUERY, {"login": login, "from": from_iso, "to": to_iso})
    user = data["user"]

    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    repos = user["repositories"]["nodes"]

    outputs = {
        "stats.svg": build_stats_svg(days),
        "streak.svg": build_streak_svg(days),
        "langs.svg": build_langs_svg(repos),
        "year.svg": build_year_svg(days),
    }
    for name, svg in outputs.items():
        with open(name, "w") as f:
            f.write(svg)
    print(f"[stats] wrote {', '.join(outputs)}", file=sys.stderr)


if __name__ == "__main__":
    main()
