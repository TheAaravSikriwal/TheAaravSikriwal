"""
Generate an animated SVG of a UFO abducting GitHub contribution stars,
with a chasing rocket firing lasers at it.

Path: visits every star in order of contribution count (least -> most),
so the chase ends on your busiest day. UFO leads, ship trails by ~8 cells.

Outputs:
  dist/github-contribution-grid-ufo.svg
  dist/github-contribution-grid-ufo-dark.svg
"""

import os
import sys
import json
import urllib.request
from datetime import datetime

# ---------- config ----------
CELL = 14
PAD_X = 30
PAD_Y = 40
WEEKS = 53
DAYS = 7
DURATION = 30           # seconds for full loop
TRAIL_OFFSET = 8        # how many cells back the ship trails
GREEN = "#39FF14"
DARK_BG = "#000000"
LIGHT_BG = "#ffffff"
DARK_STAR = "#39FF14"
LIGHT_STAR = "#216e39"
EMPTY_OPACITY = 0.12


def fetch_contributions(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays { contributionCount date }
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
    grid = [[0] * DAYS for _ in range(WEEKS)]
    for w_i, week in enumerate(weeks[-WEEKS:]):
        for day in week["contributionDays"]:
            d = datetime.fromisoformat(day["date"]).weekday()
            row = (d + 1) % 7
            if w_i < WEEKS:
                grid[w_i][row] = day["contributionCount"]
    return grid


def star_points(cx, cy, r_out, r_in=None):
    """Return polygon points string for a 5-point star centered at (cx, cy)."""
    import math
    if r_in is None:
        r_in = r_out * 0.4
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        angle = -math.pi / 2 + i * math.pi / 5
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        pts.append(f"{x:.2f},{y:.2f}")
    return " ".join(pts)


def cell_center(w, d):
    cx = PAD_X + w * CELL + CELL / 2
    cy = PAD_Y + d * CELL + CELL / 2
    return cx, cy


def build_path(coords):
    """SVG path 'M x,y L x,y L x,y...' through a list of (x, y)."""
    if not coords:
        return "M 0,0"
    parts = [f"M {coords[0][0]:.1f},{coords[0][1]:.1f}"]
    for x, y in coords[1:]:
        parts.append(f"L {x:.1f},{y:.1f}")
    return " ".join(parts)


def build_svg(grid, dark=True):
    bg = DARK_BG if dark else LIGHT_BG
    star_color = DARK_STAR if dark else LIGHT_STAR
    accent = GREEN

    width = PAD_X * 2 + WEEKS * CELL
    height = PAD_Y * 2 + DAYS * CELL + 30

    # Build ordered visit path: least -> most commits
    # Skip cells with 0 commits (we still draw them faintly, just don't visit)
    filled = []
    for w in range(WEEKS):
        for d in range(DAYS):
            if grid[w][d] > 0:
                filled.append((grid[w][d], w, d))
    filled.sort(key=lambda x: (x[0], x[1], x[2]))  # ascending by commits
    visit_order = [(w, d) for _, w, d in filled]

    if not visit_order:
        # No contributions in last year — degrade gracefully
        visit_order = [(0, 0), (WEEKS - 1, DAYS - 1)]

    # Coordinate path for UFO: entry from off-screen left, visit each cell, exit right
    ufo_coords = [(-30, PAD_Y - 20)]
    for w, d in visit_order:
        ufo_coords.append(cell_center(w, d))
    ufo_coords.append((width + 30, PAD_Y - 20))
    ufo_path = build_path(ufo_coords)

    # Ship path: same shape but offset back in time (we use a separate path
    # that starts further off-screen so when it animates with the same duration
    # it's visually behind the UFO).
    # Trick: pad the start with extra coordinates so the ship "catches up"
    # to where the UFO was TRAIL_OFFSET steps ago.
    ship_start_pad = [(-30 - i * 20, PAD_Y - 20) for i in range(TRAIL_OFFSET, 0, -1)]
    ship_coords = ship_start_pad + ufo_coords[:-TRAIL_OFFSET]
    ship_coords.append((width + 30, PAD_Y - 20))
    ship_path = build_path(ship_coords)

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" style="background:{bg}">'
    )

    # defs: gradients for ufo dome, beam, engine glow
    parts.append(f'''<defs>
      <radialGradient id="dome" cx="50%" cy="40%" r="60%">
        <stop offset="0%" stop-color="#aaffaa" stop-opacity="0.95"/>
        <stop offset="60%" stop-color="{accent}" stop-opacity="0.7"/>
        <stop offset="100%" stop-color="{accent}" stop-opacity="0.1"/>
      </radialGradient>
      <radialGradient id="beam" cx="50%" cy="0%" r="80%">
        <stop offset="0%" stop-color="{accent}" stop-opacity="0.6"/>
        <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="flame" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#fff8aa"/>
        <stop offset="40%" stop-color="#ffb84d"/>
        <stop offset="100%" stop-color="#ff3300" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="laserGlow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#ffffff"/>
        <stop offset="40%" stop-color="{accent}"/>
        <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
      </radialGradient>
    </defs>''')

    parts.append(f'<rect width="{width}" height="{height}" fill="{bg}"/>')

    # Background twinkling stars in the padding area
    if dark:
        import random
        random.seed(7)
        bg_stars = []
        for _ in range(60):
            sx = random.randint(0, width)
            sy = random.randint(0, height)
            # avoid grid area
            if PAD_Y - 5 < sy < PAD_Y + DAYS * CELL + 5 and PAD_X - 5 < sx < PAD_X + WEEKS * CELL + 5:
                continue
            r = random.uniform(0.4, 1.2)
            op = random.uniform(0.3, 0.8)
            bg_stars.append(
                f'<circle cx="{sx}" cy="{sy}" r="{r:.1f}" fill="{star_color}" opacity="{op:.2f}">'
                f'<animate attributeName="opacity" values="{op:.2f};{op*0.3:.2f};{op:.2f}" '
                f'dur="{random.uniform(2,5):.1f}s" repeatCount="indefinite"/>'
                f'</circle>'
            )
        parts.extend(bg_stars)

    # Contribution stars (5-pointed)
    # Each cell's star fades out when its turn in visit_order comes up.
    total_visits = len(visit_order)
    for w in range(WEEKS):
        for d in range(DAYS):
            cx, cy = cell_center(w, d)
            count = grid[w][d]
            if count == 0:
                # empty/faint placeholder star
                pts = star_points(cx, cy, 2.5)
                parts.append(
                    f'<polygon points="{pts}" fill="{star_color}" opacity="{EMPTY_OPACITY}"/>'
                )
            else:
                # size scales subtly with count (3.5 - 6 px outer radius)
                r_out = 3.5 + min(count / 10.0, 1.0) * 2.5
                pts = star_points(cx, cy, r_out)
                # find when this cell is visited
                try:
                    idx = visit_order.index((w, d))
                except ValueError:
                    idx = 0
                t = (idx + 1) / (total_visits + 2)  # +2 for entry/exit padding
                fade_start = max(0, t - 0.003)
                fade_end = min(1, t + 0.012)
                parts.append(
                    f'<polygon points="{pts}" fill="{accent}">'
                    f'<animate attributeName="opacity" '
                    f'values="1;1;0;0;1" '
                    f'keyTimes="0;{fade_start:.4f};{fade_end:.4f};0.98;1" '
                    f'dur="{DURATION}s" repeatCount="indefinite"/>'
                    f'</polygon>'
                )

    # ---------- UFO ----------
    # Group with tractor beam BEHIND the saucer body
    parts.append(f'''<g>
      <animateMotion dur="{DURATION}s" repeatCount="indefinite" rotate="0" path="{ufo_path}"/>
      <!-- tractor beam (downward cone) -->
      <path d="M -10,2 L 10,2 L 22,40 L -22,40 Z" fill="url(#beam)"/>
      <!-- saucer disc -->
      <ellipse cx="0" cy="0" rx="20" ry="6" fill="#2d2d2d" stroke="{accent}" stroke-width="1"/>
      <ellipse cx="0" cy="-2" rx="20" ry="3" fill="#444"/>
      <!-- rim lights -->
      <circle cx="-14" cy="1" r="1.4" fill="{accent}"><animate attributeName="opacity" values="1;0.3;1" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="-7" cy="2" r="1.4" fill="{accent}"><animate attributeName="opacity" values="0.3;1;0.3" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="0" cy="2.5" r="1.4" fill="{accent}"><animate attributeName="opacity" values="1;0.3;1" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="7" cy="2" r="1.4" fill="{accent}"><animate attributeName="opacity" values="0.3;1;0.3" dur="0.6s" repeatCount="indefinite"/></circle>
      <circle cx="14" cy="1" r="1.4" fill="{accent}"><animate attributeName="opacity" values="1;0.3;1" dur="0.6s" repeatCount="indefinite"/></circle>
      <!-- dome -->
      <ellipse cx="0" cy="-4" rx="9" ry="7" fill="url(#dome)" stroke="{accent}" stroke-width="0.8"/>
      <ellipse cx="-2" cy="-6" rx="3" ry="2" fill="#ffffff" opacity="0.4"/>
    </g>''')

    # ---------- Rocket / spaceship ----------
    # rotated 90deg-ish naturally because animateMotion's rotate="auto" would
    # spin it through every turn; we keep rotate=0 to keep orientation steady.
    # Draw the rocket pointing right (toward where ufo is going).
    parts.append(f'''<g>
      <animateMotion dur="{DURATION}s" repeatCount="indefinite" rotate="0" path="{ship_path}"/>
      <!-- engine flame (behind body) -->
      <ellipse cx="-14" cy="0" rx="8" ry="3.5" fill="url(#flame)">
        <animate attributeName="rx" values="6;10;6" dur="0.25s" repeatCount="indefinite"/>
      </ellipse>
      <!-- fuselage -->
      <path d="M -10,-4 L 8,-4 L 14,0 L 8,4 L -10,4 Z" fill="#cccccc" stroke="{accent}" stroke-width="1"/>
      <!-- nose cone -->
      <path d="M 8,-4 L 14,0 L 8,4 Z" fill="{accent}"/>
      <!-- cockpit window -->
      <circle cx="2" cy="0" r="2.2" fill="#88ddff" stroke="{accent}" stroke-width="0.6"/>
      <!-- wings/fins -->
      <path d="M -6,-4 L -10,-9 L -4,-4 Z" fill="{accent}"/>
      <path d="M -6,4 L -10,9 L -4,4 Z" fill="{accent}"/>
      <!-- laser bolt firing forward -->
      <line x1="14" y1="0" x2="38" y2="0" stroke="{accent}" stroke-width="2" stroke-linecap="round">
        <animate attributeName="opacity" values="1;0;1;0;1" dur="0.6s" repeatCount="indefinite"/>
        <animate attributeName="x2" values="18;50;18" dur="0.6s" repeatCount="indefinite"/>
      </line>
      <circle cx="38" cy="0" r="2.5" fill="url(#laserGlow)">
        <animate attributeName="opacity" values="1;0;1;0;1" dur="0.6s" repeatCount="indefinite"/>
        <animate attributeName="cx" values="18;50;18" dur="0.6s" repeatCount="indefinite"/>
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
