from io import BytesIO

from PIL import Image

from share_card import build_share_card


def test_share_card_is_valid_png():
    data = build_share_card(
        merchant="ร้านตัวอย่าง",
        people=["A", "B", "C"],
        totals={"A": 50.0, "B": 50.0, "C": 100.0},
        calculated_total=200.0,
        receipt_total=200.0,
        items=[
            {"label": "กะเพรา #1", "price": 100.0, "people": ["A", "B"]},
            {"label": "กะเพรา #2", "price": 100.0, "people": ["C"]},
        ],
    )
    image = Image.open(BytesIO(data))
    assert image.format == "PNG"
    assert image.width == 1080
    assert image.height > 500
