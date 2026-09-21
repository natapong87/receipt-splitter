from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


_THAI_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansThai-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThaiUI-Regular.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/LeelawUI.ttf",
    "/System/Library/Fonts/Thonburi.ttc",
]
_THAI_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansThai-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThaiUI-Bold.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
    "C:/Windows/Fonts/LeelaUIb.ttf",
    "/System/Library/Fonts/Thonburi.ttc",
]
_LATIN_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_LATIN_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _find_font(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _load_font(size: int, *, thai: bool, bold: bool = False):
    if thai:
        candidates = _THAI_BOLD_CANDIDATES if bold else _THAI_REGULAR_CANDIDATES
    else:
        candidates = _LATIN_BOLD_CANDIDATES if bold else _LATIN_REGULAR_CANDIDATES
    path = _find_font(candidates)
    if path:
        return ImageFont.truetype(path, size=size)
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _is_thai_char(ch: str) -> bool:
    code = ord(ch)
    return 0x0E00 <= code <= 0x0E7F


def _runs(text: str):
    text = str(text)
    if not text:
        return []
    result = []
    current_is_thai = _is_thai_char(text[0])
    current = [text[0]]
    for ch in text[1:]:
        is_thai = _is_thai_char(ch)
        # Spaces stay with the current run to avoid unnecessary font switches.
        if ch.isspace() or is_thai == current_is_thai:
            current.append(ch)
        else:
            result.append(("".join(current), current_is_thai))
            current = [ch]
            current_is_thai = is_thai
    result.append(("".join(current), current_is_thai))
    return result


def _mixed_width(draw: ImageDraw.ImageDraw, text: str, size: int, bold: bool = False) -> float:
    width = 0.0
    for run, thai in _runs(text):
        font = _load_font(size, thai=thai, bold=bold)
        bbox = draw.textbbox((0, 0), run, font=font)
        width += bbox[2] - bbox[0]
    return width


def _draw_mixed(draw: ImageDraw.ImageDraw, xy, text: str, *, size: int, bold: bool = False, fill="black", anchor_right: bool = False):
    x, y = xy
    if anchor_right:
        x -= _mixed_width(draw, text, size, bold)
    for run, thai in _runs(text):
        font = _load_font(size, thai=thai, bold=bold)
        draw.text((x, y), run, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), run, font=font)
        x += bbox[2] - bbox[0]


def _money(value: float) -> str:
    return f"{float(value):,.2f} บาท"


def build_share_card(
    *,
    merchant: str,
    people: list[str],
    totals: dict[str, float],
    calculated_total: float,
    receipt_total: float,
    items: list[dict] | None = None,
) -> bytes:
    """Create a mobile-friendly PNG summary card and return PNG bytes."""
    items = items or []
    width = 1080
    margin = 72
    row_h = 92
    item_line_h = 52
    assigned_items = [i for i in items if i.get("people")]
    details_height = 0
    if assigned_items:
        details_height = 105 + min(len(assigned_items), 12) * item_line_h
        if len(assigned_items) > 12:
            details_height += item_line_h
    height = 330 + max(1, len(people)) * row_h + details_height + 230
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    y = margin
    _draw_mixed(draw, (margin, y), "สรุปหารบิล", size=54, bold=True)
    y += 78
    _draw_mixed(draw, (margin, y), merchant.strip() or "มื้อนี้", size=30)
    y += 68
    draw.line((margin, y, width - margin, y), fill="#D8D8D8", width=3)
    y += 42
    _draw_mixed(draw, (margin, y), "คน", size=32, bold=True)
    _draw_mixed(draw, (width - margin, y), "ต้องจ่าย", size=32, bold=True, anchor_right=True)
    y += 62

    for person in people:
        _draw_mixed(draw, (margin, y), str(person), size=31)
        _draw_mixed(draw, (width - margin, y), _money(totals.get(person, 0.0)), size=32, bold=True, anchor_right=True)
        y += row_h

    draw.line((margin, y, width - margin, y), fill="#D8D8D8", width=3)
    y += 36
    _draw_mixed(draw, (margin, y), "รวมที่แบ่งแล้ว", size=32, bold=True)
    _draw_mixed(draw, (width - margin, y), _money(calculated_total), size=32, bold=True, anchor_right=True)
    y += 62

    if receipt_total > 0:
        _draw_mixed(draw, (margin, y), "ยอดบนใบเสร็จ", size=31)
        _draw_mixed(draw, (width - margin, y), _money(receipt_total), size=31, anchor_right=True)
        y += 58

    if assigned_items:
        y += 18
        draw.line((margin, y, width - margin, y), fill="#D8D8D8", width=3)
        y += 38
        _draw_mixed(draw, (margin, y), "รายการ", size=32, bold=True)
        y += 58
        for item in assigned_items[:12]:
            people_text = ", ".join(item.get("people", []))
            label = str(item.get("label") or item.get("name") or "รายการ")
            line = f"{label} • {people_text}"
            _draw_mixed(draw, (margin, y), line[:52], size=25)
            _draw_mixed(draw, (width - margin, y), _money(float(item.get("price", 0))), size=25, anchor_right=True)
            y += item_line_h
        if len(assigned_items) > 12:
            _draw_mixed(draw, (margin, y), f"และอีก {len(assigned_items) - 12} รายการ", size=25)
            y += item_line_h

    y += 26
    draw.line((margin, y, width - margin, y), fill="#D8D8D8", width=3)
    y += 34
    _draw_mixed(draw, (margin, y), "Receipt Splitter", size=25, fill="#555555")
    y += 42
    _draw_mixed(draw, (margin, y), "ตรวจสอบยอดก่อนโอนเงินทุกครั้ง", size=25, fill="#555555")

    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()
