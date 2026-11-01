# Builds the langify.org mark and wordmark from Geist Mono SemiBold outlines (SIL OFL 1.1).
# Run from this directory (Chrome is used for the PNG export):
#   nix-shell -p 'python3.withPackages(p:[p.fonttools])' --run 'python3 build.py'
import os
import re
import subprocess
import urllib.request

from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONT = "font/GeistMono-SemiBold.ttf"
FONT_URL = "https://fonts.gstatic.com/s/geistmono/v6/or3yQ6H-1_WfwkMZI_qYPLs1a-t7PU0AbeHjL55T.ttf"
LIGHT = {"ink": "#111111", "accent": "#E04000", "muted": "#8A8F98"}  # on white
DARK = {"ink": "#F5F7FA", "accent": "#FF4F00", "muted": "#7D8590"}   # on #0d1117
TRACK = -40      # font units per glyph (-0.04em)
STEP = 600 + TRACK
ARM_EXT = 20     # accent arm runs 20 units past the glyph's own foot (x 548); >60 hits the 'a'

if not os.path.exists(FONT):
    os.makedirs("font", exist_ok=True)
    urllib.request.urlretrieve(FONT_URL, FONT)
font = TTFont(FONT)
gs, cmap = font.getGlyphSet(), font.getBestCmap()


def contours(ch, dx=0):
    """Each contour of a glyph as an SVG path in y-down font units, shifted by dx."""
    rec = DecomposingRecordingPen(gs)  # resolve composites such as 'i'
    gs[cmap[ord(ch)]].draw(rec)
    out, cur = [], RecordingPen()
    for op, pts in rec.value:
        cur.value.append((op, pts))
        if op in ("closePath", "endPath"):
            pen = SVGPathPen(gs)
            cur.replay(TransformPen(pen, (1, 0, 0, -1, dx, 0)))
            out.append(pen.getCommands())
            cur = RecordingPen()
    return out


def glyph(ch, dx, fill):
    return f'<path d="{"".join(contours(ch, dx))}" fill="{fill}"/>'  # one path keeps counters open


def mark_l(dx, c):
    """Geist Mono 'l' without the foot's left half: ink stem+hook down to the baseline,
    accent only on the arm right of the stem (stem x 255..373, foot y 0..96)."""
    stem, _foot = contours("l", dx)
    stem, n = re.subn(r"(?<=[ V])-34(?![\d.])", "0", stem)  # stem bottom y=34 (inside the foot) -> baseline
    assert n == 2, stem
    return (f'<path d="{stem}" fill="{c["ink"]}"/>'
            f'<path d="M{373 + dx} 0V-96H{548 + ARM_EXT + dx}V0Z" fill="{c["accent"]}"/>')


def svg(body, w, h, vb, bg=None):
    vb_s = " ".join(f"{v:g}" for v in vb)
    rect = f'<rect x="{vb[0]:g}" y="{vb[1]:g}" width="{vb[2]:g}" height="{vb[3]:g}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb_s}">{rect}{body}</svg>\n'


def mark():
    x0, x1, side = 72, 548 + ARM_EXT, 1240  # glyph height 710 -> ~57% of the canvas
    cx, cy = (x0 + x1) / 2, -355
    return svg(mark_l(0, LIGHT), 512, 512, (cx - side / 2, cy - side / 2, side, side), "#FFFFFF")


def wordmark(c):
    body = mark_l(0, c) + "".join(
        glyph(ch, i * STEP, c["ink"] if i < 7 else c["muted"]) for i, ch in enumerate("langify.org") if i)
    width, asc, desc = 10 * STEP + 600, 760, 260  # covers ascenders and g/y descenders
    return svg(body, round(width / 10), round((asc + desc) / 10), (0, -asc, width, asc + desc))


def render(svg_file, png_file, w, h):
    html = os.path.abspath(png_file + ".html")
    with open(html, "w") as f:
        f.write(f'<body style="margin:0"><img src="{os.path.abspath(svg_file)}" width="{w}" height="{h}">')
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--screenshot={os.path.abspath(png_file)}", f"--window-size={w},{h}", "file://" + html],
                   check=True, capture_output=True)
    os.remove(html)


open("mark.svg", "w").write(mark())
open("wordmark.svg", "w").write(wordmark(LIGHT))
open("wordmark-dark.svg", "w").write(wordmark(DARK))
render("mark.svg", "avatar.png", 1024, 1024)
print("ok")
