from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


_FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _find_font(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _load_font(size: int, *, bold: bool = False):
    candidates = _FONT_BOLD_CANDIDATES if bold else _FONT_REGULAR_CANDIDATES
    path = _find_font(candidates)
    if path:
        return ImageFont.truetype(path, size=size)

    try:
        fallback = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(fallback, size=size)
    except OSError:
        return ImageFont.load_default()


def _english_text(value: object, fallback: str) -> str:
    """Return ASCII-only text so the exported image works on every host.

    Thai and other non-ASCII user-entered values are replaced with a clear
    English fallback instead of being rendered as square boxes.
    """

    text = " ".join(str(value or "").strip().split())
    if not text or any(ord(ch) > 127 for ch in text):
        return fallback
    return text


def _text_width(draw: ImageDraw.ImageDraw, text: str, size: int, bold: bool = False) -> int:
    font = _load_font(size, bold=bold)
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _draw(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    size: int,
    bold: bool = False,
    fill: str = "#20252C",
    right: bool = False,
) -> None:
    x, y = xy
    font = _load_font(size, bold=bold)
    if right:
        x -= _text_width(draw, text, size, bold)
    draw.text((x, y), text, font=font, fill=fill)


def _money(value: object) -> str:
    return f"THB {float(value):,.2f}"


def build_share_card(*, merchant, people, totals, calculated_total, receipt_total, items=None) -> bytes:
    """Build an English-only PNG summary.

    The Streamlit app itself remains in Thai. The downloaded PNG deliberately
    uses ASCII-only text because font availability differs between local PCs
    and Streamlit Cloud. Thai member, merchant, and item names receive stable
    English labels such as ``Member 1`` and ``Item 1``.
    """

    items = items or []
    people = list(people)

    member_labels = {
        person: _english_text(person, f"Member {index}")
        for index, person in enumerate(people, start=1)
    }

    assigned_items = [item for item in items if item.get("people")][:10]

    width = 1080
    margin = 70
    row_h = 82
    items_h = 0 if not assigned_items else 95 + len(assigned_items) * 48
    height = 330 + max(1, len(people)) * row_h + items_h + 220

    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)

    y = margin
    draw.rounded_rectangle((margin, y, margin + 92, y + 58), radius=18, fill="#EAF3FF")
    _draw(draw, (margin + 15, y + 13), "THB", size=25, bold=True, fill="#397DCC")
    _draw(draw, (margin + 112, y + 5), "Bill Summary", size=48, bold=True)
    y += 74
    merchant_label = _english_text(merchant, "Shared meal")
    _draw(draw, (margin, y), merchant_label, size=27, fill="#7D8794")
    y += 58

    draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
    y += 30
    _draw(draw, (margin, y), "Member", size=28, bold=True)
    _draw(draw, (width - margin, y), "Amount", size=28, bold=True, right=True)
    y += 52

    for person in people:
        _draw(draw, (margin, y), member_labels[person], size=28, bold=True)
        _draw(draw, (width - margin, y), _money(totals.get(person, 0)), size=28, bold=True, right=True)
        y += row_h

    draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
    y += 28
    _draw(draw, (margin, y), "Total", size=30, bold=True)
    _draw(draw, (width - margin, y), _money(calculated_total), size=30, bold=True, right=True)
    y += 52
    if receipt_total:
        _draw(draw, (margin, y), "Receipt total", size=24, fill="#7D8794")
        _draw(draw, (width - margin, y), _money(receipt_total), size=24, fill="#7D8794", right=True)
        y += 48

    if assigned_items:
        y += 8
        draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
        y += 28
        _draw(draw, (margin, y), "Items", size=28, bold=True)
        y += 48

        for index, item in enumerate(assigned_items, start=1):
            raw_label = item.get("name") or item.get("label")
            item_label = _english_text(raw_label, f"Item {index}")

            consumers = []
            for person in item.get("people", []):
                consumers.append(
                    member_labels.get(person, _english_text(person, "Member"))
                )

            people_text = ", ".join(consumers) or "Unassigned"
            line = f"{item_label} - {people_text}"
            _draw(draw, (margin, y), line[:60], size=22)
            _draw(draw, (width - margin, y), _money(item.get("price", 0)), size=22, right=True)
            y += 48

    y += 24
    draw.line((margin, y, width - margin, y), fill="#E7EBF0", width=3)
    y += 24
    _draw(draw, (margin, y), "Split Bill", size=21, fill="#9AA2AD")
    _draw(
        draw,
        (width - margin, y),
        "Please verify totals before payment",
        size=21,
        fill="#9AA2AD",
        right=True,
    )

    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()
