from io import BytesIO

from PIL import Image

from share_card import _english_text, build_share_card


def test_english_text_keeps_ascii_and_replaces_thai():
    assert _english_text("Nat", "Member 1") == "Nat"
    assert _english_text("สมาชิกเอ", "Member 1") == "Member 1"
    assert _english_text("กะเพรา #1", "Item 1") == "Item 1"


def test_share_card_is_valid_png_with_thai_input():
    data = build_share_card(
        merchant="ร้านตัวอย่าง",
        people=["A", "บี", "C"],
        totals={"A": 50.0, "บี": 50.0, "C": 100.0},
        calculated_total=200.0,
        receipt_total=200.0,
        items=[
            {"label": "กะเพรา #1", "price": 100.0, "people": ["A", "บี"]},
            {"label": "Burger #2", "price": 100.0, "people": ["C"]},
        ],
    )
    image = Image.open(BytesIO(data))
    assert image.format == "PNG"
    assert image.width == 1080
    assert image.height > 500
