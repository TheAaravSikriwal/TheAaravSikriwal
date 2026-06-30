"""
Generate an animated SVG: UFO abducting GitHub contribution stars,
chased by a rocket whose nose tracks the UFO.

Path: visits cells in order of contribution count (least -> most).
"""

import os
import sys
import json
import math
import random
import urllib.request
from datetime import datetime

# ---------- config ----------
CELL = 14
PAD_X = 30
PAD_Y = 40
WEEKS = 53
DAYS = 7
DURATION = 30           # seconds for full loop
TRAIL = 3               # how many cells back the ship trails (close chase)

# Realistic space palette
BG_DARK = "#0a0e27"     # deep navy
BG_DARK_2 = "#1a1147"   # purple nebula tone
BG_LIGHT = "#ffffff"
STAR_WHITE = "#ffffff"
STAR_GOLD = "#ffd86b"
STAR_BLUE = "#9fd8ff"
STAR_LIGHT = "#3a3a3a"  # for light mode
UFO_BODY = "#8fa3b3"    # metallic silver
UFO_RIM = "#2dd4d4"     # teal accent
UFO_DOME = "#7fffd4"
ROCKET_BODY = "#f5f5f5" # white
ROCKET_ACCENT = "#e63946" # red
ROCKET_WINDOW = "#7fc8ff"
LASER = "#00f0ff"       # cyan laser
FLAME_HOT = "#fff3a0"
FLAME_MID = "#ffaa3d"
FLAME_OUT = "#ff3c00"


def fetch_contributions(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks { contributionDays { contributionCount date } }
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
    grid = [[0] * DAYS for _ in range(WEEKS)]
    for w_i, week in enumerate(weeks[-WEEKS:]):
        for day in week["contributionDays"]:
            d = datetime.fromisoformat(day["date"]).weekday()
            row = (d + 1) % 7
            if w_i < WEEKS:
                grid[w_i][row] = day["contributionCount"]
    return grid


def star_points(cx, cy, r_out, r_in=None):
    if r_in is None:
        r_in = r_out * 0.42
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        angle = -math.pi / 2 + i * math.pi / 5
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        pts.append(f"{x:.2f},{y:.2f}")
    return " ".join(pts)


def cell_center(w, d):
    return (PAD_X + w * CELL + CELL / 2, PAD_Y + d * CELL + CELL / 2)


def build_path(coords):
    if not coords:
        return "M 0,0"
    parts = [f"M {coords[0][0]:.1f},{coords[0][1]:.1f}"]
    for x, y in coords[1:]:
        parts.append(f"L {x:.1f},{y:.1f}")
    return " ".join(parts)


def build_svg(grid, dark=True):
    bg = BG_DARK if dark else BG_LIGHT
    width = PAD_X * 2 + WEEKS * CELL
    height = PAD_Y * 2 + DAYS * CELL + 30

    # Build visit order: least -> most commits
    filled = []
    for w in range(WEEKS):
        for d in range(DAYS):
            if grid[w][d] > 0:
                filled.append((grid[w][d], w, d))
    filled.sort(key=lambda x: (x[0], x[1], x[2]))
    visit_order = [(w, d) for _, w, d in filled]
    if not visit_order:
        visit_order = [(0, 0), (WEEKS - 1, DAYS - 1)]

    # UFO path: enter from upper-left, hit each cell, exit upper-right
    ufo_coords = [(-30, PAD_Y - 20)]
    for w, d in visit_order:
        ufo_coords.append(cell_center(w, d))
    ufo_coords.append((width + 30, PAD_Y - 20))
    ufo_path = build_path(ufo_coords)

    # Ship path: same shape, lagged by TRAIL steps
    ship_pad = [(-30 - i * 15, PAD_Y - 20) for i in range(TRAIL, 0, -1)]
    ship_coords = ship_pad + ufo_coords[:-TRAIL] + [(width + 30, PAD_Y - 20)]
    ship_path = build_path(ship_coords)

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" style="background:{bg}">'
    )

    # ---------- defs ----------
    parts.append(f'''<defs>
      <radialGradient id="nebula" cx="50%" cy="40%" r="70%">
        <stop offset="0%" stop-color="{BG_DARK_2}" stop-opacity="0.55"/>
        <stop offset="60%" stop-color="{BG_DARK}" stop-opacity="0.2"/>
        <stop offset="100%" stop-color="{BG_DARK}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="dome" cx="40%" cy="35%" r="65%">
        <stop offset="0%" stop-color="#e8fff8" stop-opacity="0.95"/>
        <stop offset="55%" stop-color="{UFO_DOME}" stop-opacity="0.8"/>
        <stop offset="100%" stop-color="{UFO_RIM}" stop-opacity="0.2"/>
      </radialGradient>
      <radialGradient id="beam" cx="50%" cy="0%" r="80%">
        <stop offset="0%" stop-color="{UFO_RIM}" stop-opacity="0.55"/>
        <stop offset="100%" stop-color="{UFO_RIM}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="flame" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="{FLAME_HOT}"/>
        <stop offset="45%" stop-color="{FLAME_MID}"/>
        <stop offset="100%" stop-color="{FLAME_OUT}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="laserGlow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#ffffff"/>
        <stop offset="40%" stop-color="{LASER}"/>
        <stop offset="100%" stop-color="{LASER}" stop-opacity="0"/>
      </radialGradient>
      <linearGradient id="rocketBody" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#ffffff"/>
        <stop offset="100%" stop-color="#b8b8b8"/>
      </linearGradient>
    </defs>''')

    # background fill + nebula glow
    parts.append(f'<rect width="{width}" height="{height}" fill="{bg}"/>')
    if dark:
        parts.append(f'<rect width="{width}" height="{height}" fill="url(#nebula)"/>')

    # ---------- background twinkling stars ----------
    if dark:
        random.seed(7)
        for _ in range(85):
            sx = random.randint(0, width)
            sy = random.randint(0, height)
            # avoid grid area
            if PAD_X - 5 < sx < PAD_X + WEEKS * CELL + 5 and PAD_Y - 5 < sy < PAD_Y + DAYS * CELL + 5:
                continue
            r = random.uniform(0.4, 1.4)
            op = random.uniform(0.4, 0.95)
            color = random.choice([STAR_WHITE, STAR_WHITE, STAR_WHITE, STAR_GOLD, STAR_BLUE])
            dur = random.uniform(2, 5)
            parts.append(
                f'<circle cx="{sx}" cy="{sy}" r="{r:.1f}" fill="{color}" opacity="{op:.2f}">'
                f'<animate attributeName="opacity" values="{op:.2f};{op*0.25:.2f};{op:.2f}" '
                f'dur="{dur:.1f}s" repeatCount="indefinite"/>'
                f'</circle>'
            )

    # ---------- contribution stars ----------
    # color them based on count: low = blue, mid = white, high = gold
    total_visits = len(visit_order)
    for w in range(WEEKS):
        for d in range(DAYS):
            cx, cy = cell_center(w, d)
            count = grid[w][d]
            if count == 0:
                pts = star_points(cx, cy, 2.2)
                empty_color = STAR_WHITE if dark else STAR_LIGHT
                parts.append(
                    f'<polygon points="{pts}" fill="{empty_color}" opacity="0.10"/>'
                )
            else:
                # tier color
                if count >= 8:
                    color = STAR_GOLD
                    r_out = 6.5
                elif count >= 4:
                    color = STAR_WHITE
                    r_out = 5.5
                else:
                    color = STAR_BLUE
                    r_out = 4.5
                pts = star_points(cx, cy, r_out)
                try:
                    idx = visit_order.index((w, d))
                except ValueError:
                    idx = 0
                t = (idx + 1) / (total_visits + 2)
                # tight fade: ~0.2% of duration each side — pops out on contact
                fade_start = max(0, t - 0.001)
                fade_end = min(1, t + 0.002)
                parts.append(
                    f'<polygon points="{pts}" fill="{color}">'
                    f'<animate attributeName="opacity" '
                    f'values="1;1;0;0;1" '
                    f'keyTimes="0;{fade_start:.4f};{fade_end:.4f};0.99;1" '
                    f'dur="{DURATION}s" repeatCount="indefinite"/>'
                    f'</polygon>'
                )

    # ---------- UFO ----------
    parts.append(f'''<g>
      <animateMotion dur="{DURATION}s" repeatCount="indefinite" rotate="0" path="{ufo_path}"/>
      <!-- tractor beam (downward cone) -->
      <path d="M -10,2 L 10,2 L 22,42 L -22,42 Z" fill="url(#beam)"/>
      <!-- saucer body (metallic) -->
      <ellipse cx="0" cy="0" rx="22" ry="6" fill="{UFO_BODY}" stroke="{UFO_RIM}" stroke-width="0.8"/>
      <ellipse cx="0" cy="-2" rx="22" ry="3" fill="#c4d2dc"/>
      <ellipse cx="0" cy="3" rx="22" ry="2.5" fill="#5a6b7a"/>
      <!-- rim lights, alternating pulse -->
      <circle cx="-16" cy="2" r="1.5" fill="{UFO_RIM}"><animate attributeName="opacity" values="1;0.3;1" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="-8" cy="3" r="1.5" fill="{UFO_RIM}"><animate attributeName="opacity" values="0.3;1;0.3" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="0" cy="3.5" r="1.5" fill="{UFO_RIM}"><animate attributeName="opacity" values="1;0.3;1" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="8" cy="3" r="1.5" fill="{UFO_RIM}"><animate attributeName="opacity" values="0.3;1;0.3" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="16" cy="2" r="1.5" fill="{UFO_RIM}"><animate attributeName="opacity" values="1;0.3;1" dur="0.6s" repeatCount="indefinite"/></circle>
      <!-- dome -->
      <ellipse cx="0" cy="-5" rx="10" ry="8" fill="url(#dome)" stroke="{UFO_RIM}" stroke-width="0.8"/>
      <ellipse cx="-3" cy="-8" rx="3" ry="2" fill="#ffffff" opacity="0.5"/>
    </g>''')

    # ---------- Rocket with auto-rotating nose ----------
    # Use rotate="auto" so the ship orients along its path automatically
    parts.append(f'''<g>
      <animateMotion dur="{DURATION}s" repeatCount="indefinite" rotate="auto" path="{ship_path}"/>
      <!-- engine flame -->
      <ellipse cx="-15" cy="0" rx="9" ry="3.5" fill="url(#flame)">
        <animate attributeName="rx" values="6;11;6" dur="0.22s" repeatCount="indefinite"/>
      </ellipse>
      <!-- fuselage (white with red accent stripes, NASA-ish) -->
      <path d="M -10,-4 L 9,-4 L 15,0 L 9,4 L -10,4 Z" fill="url(#rocketBody)" stroke="{ROCKET_ACCENT}" stroke-width="0.8"/>
      <!-- red nose cap -->
      <path d="M 9,-4 L 15,0 L 9,4 Z" fill="{ROCKET_ACCENT}"/>
      <!-- red stripe -->
      <rect x="-2" y="-4" width="3" height="8" fill="{ROCKET_ACCENT}"/>
      <!-- cockpit window -->
      <circle cx="4" cy="0" r="2.2" fill="{ROCKET_WINDOW}" stroke="#2a4d6e" stroke-width="0.6"/>
      <circle cx="3" cy="-0.5" r="0.8" fill="#ffffff" opacity="0.7"/>
      <!-- fins -->
      <path d="M -6,-4 L -11,-9 L -3,-4 Z" fill="{ROCKET_ACCENT}"/>
      <path d="M -6,4 L -11,9 L -3,4 Z" fill="{ROCKET_ACCENT}"/>
      <!-- laser bolt firing forward toward UFO -->
      <line x1="15" y1="0" x2="42" y2="0" stroke="{LASER}" stroke-width="2.2" stroke-linecap="round">
        <animate attributeName="opacity" values="1;0;1;0;1" dur="0.5s" repeatCount="indefinite"/>
        <animate attributeName="x2" values="20;52;20" dur="0.5s" repeatCount="indefinite"/>
      </line>
      <circle cx="42" cy="0" r="3" fill="url(#laserGlow)">
        <animate attributeName="opacity" values="1;0;1;0;1" dur="0.5s" repeatCount="indefinite"/>
        <animate attributeName="cx" values="20;52;20" dur="0.5s" repeatCount="indefinite"/>
      </circle>
    </g>''')

    parts.append('</svg>')
    return "".join(parts)


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
    with open("dist/github-contribution-grid-ufo-dark.svg", "w") as f:
        f.write(build_svg(grid, dark=True))
    with open("dist/github-contribution-grid-ufo.svg", "w") as f:
        f.write(build_svg(grid, dark=False))
    print("Wrote dist/github-contribution-grid-ufo[-dark].svg")


if __name__ == "__main__":
    main()
