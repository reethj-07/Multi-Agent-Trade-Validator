"""Generate a filled commercial invoice PNG matching bundled Acme Retail EU rules."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Output paths relative to repo root
ROOT = Path(__file__).resolve().parents[1]
OUT_CLEAN = ROOT / "samples" / "acme_commercial_invoice_filled.png"
OUT_DEGRADED = ROOT / "samples" / "acme_commercial_invoice_degraded.png"


def _fonts(size: int = 20, size_title: int = 26):
    for path in (
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return (
                ImageFont.truetype(path, size),
                ImageFont.truetype(path, size_title),
            )
        except OSError:
            continue
    f = ImageFont.load_default()
    return f, f


def draw_invoice() -> Image.Image:
    w, h = 1100, 1400
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font, font_title = _fonts()

    y = 40
    lh = 28

    def line(text: str, bold: bool = False):
        nonlocal y
        f = font_title if bold else font
        draw.text((50, y), text, fill=(0, 0, 0), font=f)
        y += lh + 4

    line("COMMERCIAL INVOICE", bold=True)
    y += 10
    line("Invoice Number: INV-2025-ACME-0099")
    line("Invoice Date: 2025-04-15")
    line("Reference / B/L: BL-SHANGHAI-ROT-77821")
    y += 16
    line("CONSIGNEE (Ship To):", bold=True)
    line("Acme Retail EU BV")
    line("Hoofdstraat 100, 3012 AB Rotterdam, Netherlands")
    line("VAT: NL123456789B01")
    y += 16
    line("SHIPMENT:", bold=True)
    line("Port of Loading: Shanghai, China")
    line("Port of Discharge: Rotterdam, Netherlands")
    line("Incoterms: FOB Shanghai")
    line("Gross Weight: 1250 KG")
    y += 16
    line("LINE ITEMS:", bold=True)
    line("Description of Goods: Laptop computers — Model X200, 14 inch, batch export 42")
    line("HS Code: 8471.30")
    line("Quantity: 200 units")
    line("Unit Price: USD 450.00")
    line("Total Amount: USD 90,000.00")
    y += 16
    line("Country of Origin: China")
    line("Packing: 40 cartons on 2 pallets")
    y += 24
    line("Authorized Signature: _________________________   Exporter: East Asia Trading Co.")

    return img


def make_degraded(src: Image.Image) -> Image.Image:
    """Small, compressed copy to simulate a bad scan."""
    small = src.resize((src.width // 2, src.height // 2), Image.Resampling.LANCZOS)
    small = small.convert("RGB")
    return small


def main() -> None:
    OUT_CLEAN.parent.mkdir(parents=True, exist_ok=True)
    clean = draw_invoice()
    clean.save(OUT_CLEAN, "PNG", optimize=True)
    degraded = make_degraded(clean)
    degraded.save(OUT_DEGRADED, "PNG", optimize=True, compress_level=9)
    print(f"Wrote {OUT_CLEAN}")
    print(f"Wrote {OUT_DEGRADED}")


if __name__ == "__main__":
    main()
    sys.exit(0)
