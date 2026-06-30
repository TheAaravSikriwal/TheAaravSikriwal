"""
Generate an animated SVG of a UFO abducting GitHub contribution squares
while a chasing spaceship fires lasers at it.

Outputs two files:
  dist/github-contribution-grid-ufo.svg       (light + dark fallback)
  dist/github-contribution-grid-ufo-dark.svg  (dark mode)

Usage (inside GitHub Action):
    python generate_ufo.py <github_username>

Requires env var GITHUB_TOKEN with default `repo` read scope (auto-provided
by Actions via secrets.GITHUB_TOKEN).
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timedelta

# ---------- config ----------
CELL = 14            # px size of each cell including gap
DOT_R = 5            # radius of contribution dot
PAD_X = 30           # left padding
PAD_Y = 30           # top padding
WEEKS = 53           # github shows ~53 weeks
DAYS = 7
DURATION = 20        # seconds for full animation loop
GREEN = "#39FF14"
BG_LIGHT = "#ffffff"
BG_DARK = "#000000"
DOT_LIGHT = "#216e39"     # standard github dark green
DOT_DARK = "#39FF14"      # phosphor green for dark
STAR_DARK = "#39FF14"
STAR_LIGHT = "#216e39"


def fetch_contributions(username, token):
    """Fetch last year of contribution data via GitHub GraphQL API."""
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "ufo-contribution-generator",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    # Flatten into a (week, day) grid. GitHub returns weeks starting on Sunday.
    grid = [[0] * DAYS for _ in range(WEEKS)]
    for w_i, week in enumerate(weeks[-WEEKS:]):
        for day in week["contributionDays"]:
            d = datetime.fromisoformat(day["date"]).weekday()
            # weekday(): Mon=0..Sun=6. GitHub rows: Sun=0..Sat=6
            row = (d + 1) % 7
            if w_i < WEEKS:
                grid[w_i][row] = day["contributionCount"]
    return grid


def plan_path(grid):
    """Pick the order in which cells get 'abducted'.

    We do a horizontal sweep, week-by-week, top-to-bottom within each week.
    Only cells with contributions > 0 get abducted; empty cells the UFO
    flies over but doesn't fade.
    """
    path = []   # list of (week, day, is_filled)
    for w in range(WEEKS):
        for d in range(DAYS):
            path.append((w, d, grid[w][d] > 0))
    return path


def build_svg(grid, dark=True):
    bg = BG_DARK if dark else BG_LIGHT
    dot = DOT_DARK if dark else DOT_LIGHT
    star = STAR_DARK if dark else STAR_LIGHT
    accent = GREEN

    width = PAD_X * 2 + WEEKS * CELL
    height = PAD_Y * 2 + DAYS * CELL + 40   # extra room for UFO/ship hovering above

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="background:{bg}" width="100%">'
    )
    parts.append(f'<rect width="{width}" height="{height}" fill="{bg}"/>')

    # decorative stars (dark mode only looks good)
    if dark:
        import random
        random.seed(42)
        star_html = []
        for _ in range(30):
            sx = random.randint(0, width)
            sy = random.randint(0, PAD_Y)
            star_html.append(f'<circle cx="{sx}" cy="{sy}" r="0.8" fill="{star}" opacity="0.5"/>')
        parts.extend(star_html)

    # contribution dots, each with fade animation timed to when the UFO passes
    total_cells = WEEKS * DAYS
    for w in range(WEEKS):
        for d in range(DAYS):
            cx = PAD_X + w * CELL + CELL / 2
            cy = PAD_Y + d * CELL + CELL / 2
            count = grid[w][d]
            if count == 0:
                # empty placeholder cell, faint
                parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="2" fill="{dot}" opacity="0.15"/>'
                )
            else:
                # filled cell — fade out when UFO passes
                cell_index = w * DAYS + d
                t = cell_index / total_cells
                # short fade window of ~2% of total duration
                fade_start = max(0, t - 0.005)
                fade_end = min(1, t + 0.015)
                parts.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{DOT_R}" fill="{accent}">'
                    f'<animate attributeName="opacity" '
                    f'values="1;1;0;0;1" '
                    f'keyTimes="0;{fade_start:.4f};{fade_end:.4f};0.97;1" '
                    f'dur="{DURATION}s" repeatCount="indefinite"/>'
                    f'</circle>'
                )

    # tractor beam (cone behind/below UFO) — moves with the UFO
    parts.append(
        f'<g opacity="0.55">'
        f'<path d="M -10 -8 L 10 -8 L 22 38 L -22 38 Z" fill="{accent}" opacity="0.35">'
        f'<animateMotion dur="{DURATION}s" repeatCount="indefinite" '
        f'path="{_ufo_path(width, height)}"/>'
        f'</path>'
        f'</g>'
    )

    # UFO
    parts.append(
        f'<g>'
        f'<animateMotion dur="{DURATION}s" repeatCount="indefinite" '
        f'path="{_ufo_path(width, height)}"/>'
        f'<ellipse cx="0" cy="0" rx="18" ry="6" fill="{accent}"/>'
        f'<ellipse cx="0" cy="-5" rx="9" ry="7" fill="{bg}" stroke="{accent}" stroke-width="1.2"/>'
        f'<circle cx="-8" cy="2" r="1.5" fill="{bg}"/>'
        f'<circle cx="0" cy="2" r="1.5" fill="{bg}"/>'
        f'<circle cx="8" cy="2" r="1.5" fill="{bg}"/>'
        f'</g>'
    )

    # chasing spaceship + lasers
    parts.append(
        f'<g>'
        f'<animateMotion dur="{DURATION}s" repeatCount="indefinite" '
        f'path="{_ship_path(width, height)}"/>'
        # ship body (arrow shape pointing right toward UFO)
        f'<path d="M -12,-7 L 10,0 L -12,7 L -6,0 Z" fill="{accent}"/>'
        f'<circle cx="-4" cy="0" r="1.8" fill="{bg}"/>'
        # laser pulse firing forward
        f'<line x1="10" y1="0" x2="40" y2="0" stroke="{accent}" stroke-width="2">'
        f'<animate attributeName="opacity" values="1;0;1;0" '
        f'dur="0.5s" repeatCount="indefinite"/>'
        f'<animate attributeName="x2" values="14;48;14" '
        f'dur="0.5s" repeatCount="indefinite"/>'
        f'</line>'
        f'</g>'
    )

    parts.append('</svg>')
    return "".join(parts)


def _ufo_path(width, height):
    """Path for the UFO: sweep across at the top, hovering above the grid."""
    y = PAD_Y - 8
    return f"M -30,{y} L {width + 30},{y}"


def _ship_path(width, height):
    """Chasing ship runs slightly behind and slightly below the UFO."""
    y = PAD_Y - 4
    return f"M -90,{y} L {width - 30},{y}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_ufo.py <github_username>", file=sys.stderr)
        sys.exit(1)

    username = sys.argv[1]
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching contributions for {username}...")
    grid = fetch_contributions(username, token)
    filled = sum(1 for w in grid for c in w if c > 0)
    print(f"Got {filled} filled cells across {WEEKS}x{DAYS} grid.")

    os.makedirs("dist", exist_ok=True)

    dark = build_svg(grid, dark=True)
    light = build_svg(grid, dark=False)

    with open("dist/github-contribution-grid-ufo-dark.svg", "w") as f:
        f.write(dark)
    with open("dist/github-contribution-grid-ufo.svg", "w") as f:
        f.write(light)

    print("Wrote dist/github-contribution-grid-ufo.svg and -dark.svg")


if __name__ == "__main__":
    main()
