#!/usr/bin/env python3
"""Reproduce the 3000 × 3000 RGB Decode the Stack podcast cover."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "static" / "images" / "podcast-cover.png"
NAVY = "#07111F"
CYAN = "#00BEDB"
LIME = "#B9F227"
WHITE = "#F7F8F4"
FONT_DIR = Path(r"C:\Windows\Fonts")


def generate() -> Path:
    image = Image.new("RGB", (3000, 3000), NAVY)
    draw = ImageDraw.Draw(image)

    def stroke(points: list[tuple[int, int]], color: str) -> None:
        width = 126
        coordinates = [(600 + x * 9, 280 + y * 9) for x, y in points]
        draw.line(coordinates, fill=color, width=width, joint="curve")
        for x, y in coordinates:
            radius = width // 2
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    def text(value: str, y: int, size: int, color: str, bold: bool = True) -> None:
        face = "segoeuib.ttf" if bold else "segoeui.ttf"
        font = ImageFont.truetype(str(FONT_DIR / face), size)
        draw.text((1500, y), value, font=font, anchor="mt", fill=color)

    stroke([(38, 42), (74, 42), (122, 100), (162, 100)], CYAN)
    stroke([(38, 100), (162, 100)], LIME)
    stroke([(38, 158), (74, 158), (122, 100), (162, 100)], LIME)
    text("DECODE", 1930, 290, WHITE)
    text("THE STACK", 2240, 290, WHITE)
    text("THE DAILY TECH BRIEFING", 2690, 78, CYAN, bold=False)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    return OUTPUT


if __name__ == "__main__":
    print(generate())
