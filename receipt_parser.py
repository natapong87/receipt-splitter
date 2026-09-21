from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

SCHEMA_EXAMPLE = {
    "merchant": "ชื่อร้าน",
    "items": [
        {"name": "ชื่อเมนู", "quantity": 2, "unit_price": 100.0, "line_total": 200.0}
    ],
    "service_charge": 0.0,
    "vat": 0.0,
    "discount": 0.0,
    "total": 200.0,
}


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def normalize_receipt(data: dict[str, Any]) -> dict[str, Any]:
    out = {
        "merchant": str(data.get("merchant") or ""),
        "items": [],
        "service_charge": float(data.get("service_charge") or 0),
        "vat": float(data.get("vat") or 0),
        "discount": float(data.get("discount") or 0),
        "total": float(data.get("total") or 0),
    }
    for idx, raw in enumerate(data.get("items") or [], start=1):
        name = str(raw.get("name") or f"รายการ {idx}").strip()
        try:
            qty = max(1, int(round(float(raw.get("quantity") or 1))))
        except Exception:
            qty = 1
        line_total = float(raw.get("line_total") or 0)
        unit_price = float(raw.get("unit_price") or 0)
        if unit_price <= 0 and line_total > 0:
            unit_price = line_total / qty
        if line_total <= 0 and unit_price > 0:
            line_total = unit_price * qty
        if unit_price < 0 or line_total < 0:
            continue
        out["items"].append(
            {
                "line_id": idx,
                "name": name,
                "quantity": qty,
                "unit_price": round(unit_price, 2),
                "line_total": round(line_total, 2),
            }
        )
    return out


def parse_receipt_image(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ยังไม่ได้ตั้งค่า GEMINI_API_KEY (หรือ GOOGLE_API_KEY) จาก Google AI Studio"
        )

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)

    prompt = f"""
คุณเป็นระบบอ่านใบเสร็จร้านอาหารจากภาพ อ่านทั้งภาษาไทยและอังกฤษ
คืนค่าเป็น JSON object เท่านั้น ห้ามมี markdown หรือคำอธิบายอื่น
รูปแบบตัวอย่าง: {json.dumps(SCHEMA_EXAMPLE, ensure_ascii=False)}

กติกา:
- items มีเฉพาะอาหาร/เครื่องดื่มหรือสินค้าที่ลูกค้าสั่งจริง
- quantity คือจำนวนที่สั่ง ถ้าในบรรทัดเดียวเขียน x2 ให้ quantity=2
- unit_price คือราคาต่อหนึ่งหน่วย ถ้ามีแต่ราคารวม ให้คำนวณจาก line_total / quantity
- line_total คือราคารวมของบรรทัดก่อน service/vat/discount
- อย่าใส่ subtotal, total, cash, change, service charge, VAT หรือ discount เป็น item
- service_charge, vat, discount ให้เป็นจำนวนเงินบาท (discount เป็นเลขบวกที่จะนำไปลบ)
- ถ้าอ่านค่าไม่ได้ให้ใช้ 0 แทน อย่าเดาเกินข้อมูลในภาพ
"""

    image = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=model,
        contents=[image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )

    if not response.text:
        raise RuntimeError("Gemini ไม่ได้ส่งข้อความกลับมา กรุณาลองรูปที่ชัดขึ้นหรือเปลี่ยนโมเดล")

    return normalize_receipt(_extract_json(response.text))
