from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


_THAI_REGULAR_CANDIDATES = [
    "/usr/share/fonts/opentype/tlwg/Loma.ttf",
    "/usr/share/fonts/opentype/tlwg/Waree.otf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansThai-Regular.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/LeelawUI.ttf",
    "/System/Library/Fonts/Thonburi.ttc",
]
_THAI_BOLD_CANDIDATES = [
    "/usr/share/fonts/opentype/tlwg/Loma-Bold.ttf",
    "/usr/share/fonts/opentype/tlwg/Loma-Bold.otf",
    "/usr/share/fonts/opentype/tlwg/Waree-Bold.otf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansThai-Bold.ttf",
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
    candidates = (_THAI_BOLD_CANDIDATES if bold else _THAI_REGULAR_CANDIDATES) if thai else (_LATIN_BOLD_CANDIDATES if bold else _LATIN_REGULAR_CANDIDATES)
    path = _find_font(candidates)
    if path:
        return ImageFont.truetype(path, size=size)
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _is_thai_char(ch: str) -> bool:
    return 0x0E00 <= ord(ch) <= 0x0E7F


def _runs(text: str):
    text = str(text)
    if not text:
        return []
    result = []
    current_thai = _is_thai_char(text[0])
    current = [text[0]]
    for ch in text[1:]:
        thai = _is_thai_char(ch)
        if ch.isspace() or thai == current_thai:
            current.append(ch)
        else:
            result.append(("".join(current), current_thai))
            current = [ch]
            current_thai = thai
    result.append(("".join(current), current_thai))
    return result


def _width(draw, text, size, bold=False):
    total = 0
    for run, thai in _runs(text):
        font = _load_font(size, thai=thai, bold=bold)
        box = draw.textbbox((0, 0), run, font=font)
        total += box[2] - box[0]
    return total


def _draw(draw, xy, text, *, size, bold=False, fill="#20252c", right=False):
    x, y = xy
    if right:
        x -= _width(draw, text, size, bold)
    for run, thai in _runs(text):
        font = _load_font(size, thai=thai, bold=bold)
        draw.text((x, y), run, font=font, fill=fill)
        box = draw.textbbox((0, 0), run, font=font)
        x += box[2] - box[0]


def _money(value):
    return f"{float(value):,.2f} บาท"


def build_share_card(*, merchant, people, totals, calculated_total, receipt_total, items=None) -> bytes:
    items = items or []

    width = 1080
    margin = 70
    row_h = 82
    item_rows = min(10, len([i for i in items if i.get("people")]))
    items_h = 0 if item_rows == 0 else 95 + item_rows * 48
    height = 330 + max(1, len(people)) * row_h + items_h + 220

    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)

    y = margin
    draw.rounded_rectangle((margin, y, margin + 58, y + 58), radius=18, fill="#EAF3FF")
    _draw(draw, (margin + 15, y + 8), "฿", size=34, bold=True, fill="#397DCC")
    _draw(draw, (margin + 78, y + 5), "สรุปหารบิล", size=48, bold=True)
    y += 74
    _draw(draw, (margin, y), merchant.strip() or "มื้อนี้", size=27, fill="#7D8794")
    y += 58

    draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
    y += 30
    _draw(draw, (margin, y), "สมาชิก", size=28, bold=True)
    _draw(draw, (width - margin, y), "ต้องรับผิดชอบ", size=28, bold=True, right=True)
    y += 52

    for person in people:
        _draw(draw, (margin, y), str(person), size=28, bold=True)
        _draw(draw, (width - margin, y), _money(totals.get(person, 0)), size=28, bold=True, right=True)
        y += row_h

    draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
    y += 28
    _draw(draw, (margin, y), "รวม", size=30, bold=True)
    _draw(draw, (width - margin, y), _money(calculated_total), size=30, bold=True, right=True)
    y += 52
    if receipt_total:
        _draw(draw, (margin, y), "ยอดบนใบเสร็จ", size=24, fill="#7D8794")
        _draw(draw, (width - margin, y), _money(receipt_total), size=24, fill="#7D8794", right=True)
        y += 48

    assigned = [i for i in items if i.get("people")][:10]
    if assigned:
        y += 8
        draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
        y += 28
        _draw(draw, (margin, y), "รายการ", size=28, bold=True)
        y += 48
        for item in assigned:
            label = str(item.get("name") or item.get("label") or "รายการ")
            persons = ", ".join(item.get("people", []))
            text = f"{label} · {persons}"
            _draw(draw, (margin, y), text[:56], size=22)
            _draw(draw, (width - margin, y), _money(item.get("price", 0)), size=22, right=True)
            y += 48

    y += 24
    draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
    y += 24
    _draw(draw, (margin, y), "Split Bill", size=21, fill="#9AA2AD")
    _draw(draw, (width - margin, y), "ตรวจสอบยอดก่อนโอนเงิน", size=21, fill="#9AA2AD", right=True)

    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()
