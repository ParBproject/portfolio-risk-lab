"""Capture README screenshots + demo GIF from the live (or local) site. Needs Playwright Chromium and ffmpeg."""
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://parbproject.github.io/portfolio-risk-lab/"
IMG = Path(__file__).resolve().parents[1] / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(600)
    pg.screenshot(path=IMG / "overview.png")
    pg.screenshot(path=IMG / "full.png", full_page=True)
    m = b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, device_scale_factor=2)
    m.goto(URL, wait_until="networkidle")
    m.wait_for_timeout(600)
    m.screenshot(path=IMG / "mobile.png")
    # GIF: switch strategies, raise costs, hover the equity curve
    tmp = Path(tempfile.mkdtemp())
    pg.set_viewport_size({"width": 1200, "height": 760})
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(400)
    n = 0

    def snap(k=1):
        global n
        for _ in range(k):
            pg.screenshot(path=tmp / f"f{n:04d}.png")
            n += 1

    snap(4)
    for name in ["Risk parity", "Black-Litterman", "60/40", "Mean-variance"]:
        pg.get_by_role("button", name=name, exact=True).click()
        pg.wait_for_timeout(150)
        snap(5)
    pg.get_by_role("button", name="20%", exact=True).click()
    snap(5)
    slider = pg.locator('input[type="range"]').first
    for v in range(10, 51, 5):
        slider.fill(str(v))
        snap(1)
    snap(4)
    box = pg.locator("svg").first.bounding_box()
    for i in range(20):
        pg.mouse.move(box["x"] + 60 + i * (box["width"] - 80) / 19, box["y"] + box["height"] / 2)
        pg.wait_for_timeout(40)
        snap(1)
    b.close()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "6", "-i", str(tmp / "f%04d.png"), "-vf",
                "scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer",
                str(IMG / "demo.gif")], check=True)
print("frames", n, "->", IMG)
