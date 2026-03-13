#!/usr/bin/env python3
"""
Generate application icon assets for packaging.
"""
from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "assets" / "icons"
PNG_PATH = OUTPUT_DIR / "wechat-scraper-icon-1024.png"
ICO_PATH = OUTPUT_DIR / "wechat-scraper.ico"
ICNS_PATH = OUTPUT_DIR / "wechat-scraper.icns"


def draw_icon(size: int = 1024) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base_draw = ImageDraw.Draw(base)
    for layer, color in enumerate([
        (20, 81, 62, 255),
        (31, 122, 86, 255),
        (70, 170, 102, 255),
        (156, 220, 111, 255),
    ]):
        inset = layer * 14
        base_draw.rounded_rectangle(
            (inset, inset, size - inset, size - inset),
            radius=220 - layer * 8,
            fill=color,
        )
    image.alpha_composite(base.filter(ImageFilter.GaussianBlur(0.5)))

    gloss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gloss_draw = ImageDraw.Draw(gloss)
    gloss_draw.ellipse((-120, -140, 760, 520), fill=(255, 255, 255, 54))
    gloss_draw.ellipse((480, 420, 1120, 1120), fill=(7, 45, 36, 80))
    image.alpha_composite(gloss)

    draw = ImageDraw.Draw(image)

    left_bubble = (170, 188, 560, 545)
    right_bubble = (432, 236, 832, 604)
    draw.ellipse(left_bubble, fill=(255, 255, 255, 250))
    draw.ellipse(right_bubble, fill=(240, 255, 244, 245))
    draw.polygon([(235, 505), (286, 458), (316, 564)], fill=(255, 255, 255, 250))
    draw.polygon([(735, 552), (666, 500), (650, 625)], fill=(240, 255, 244, 245))

    for center_x in (292, 365, 438):
        draw.ellipse((center_x - 22, 300, center_x + 22, 344), fill=(31, 122, 86, 255))
    for center_x in (538, 615, 692):
        draw.ellipse((center_x - 18, 347, center_x + 18, 383), fill=(31, 122, 86, 235))

    card = (240, 610, 784, 844)
    draw.rounded_rectangle(card, radius=72, fill=(255, 250, 240, 248))
    draw.rounded_rectangle((270, 646, 754, 808), radius=42, outline=(31, 122, 86, 180), width=10)
    for y, width in ((682, 390), (727, 322), (772, 360)):
        draw.rounded_rectangle((312, y, 312 + width, y + 20), radius=10, fill=(31, 122, 86, 235))

    draw.rounded_rectangle((648, 642, 716, 742), radius=24, fill=(117, 212, 113, 255))
    draw.polygon([(664, 742), (682, 712), (700, 742)], fill=(255, 250, 240, 248))

    stroke = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    stroke_draw = ImageDraw.Draw(stroke)
    stroke_draw.rounded_rectangle(
        (8, 8, size - 8, size - 8),
        radius=220,
        outline=(255, 255, 255, 42),
        width=10,
    )
    image.alpha_composite(stroke)
    return image


def write_icns(source: Image.Image, path: Path) -> None:
    type_map = [
        ("icp4", 16),
        ("icp5", 32),
        ("icp6", 64),
        ("ic07", 128),
        ("ic08", 256),
        ("ic09", 512),
        ("ic10", 1024),
    ]
    chunks = []
    for icon_type, size in type_map:
        resized = source.resize((size, size), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        resized.save(buffer, format="PNG")
        png_data = buffer.getvalue()
        chunks.append(icon_type.encode("ascii") + struct.pack(">I", len(png_data) + 8) + png_data)

    payload = b"".join(chunks)
    path.write_bytes(b"icns" + struct.pack(">I", len(payload) + 8) + payload)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source = draw_icon()
    source.save(PNG_PATH)
    source.save(
        ICO_PATH,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    write_icns(source, ICNS_PATH)

    print(f"Generated {PNG_PATH}")
    print(f"Generated {ICO_PATH}")
    print(f"Generated {ICNS_PATH}")


if __name__ == "__main__":
    main()
