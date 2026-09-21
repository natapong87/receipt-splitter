from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
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

DEFAULT_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]


def _secret(name: str, default: str | None = None) -> str | None:
    """Read local env first, then Streamlit Cloud secrets when available."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            value = str(st.secrets[name]).strip()
            return value or default
    except Exception:
        pass
    return default


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("AI ตอบกลับมาไม่ใช่ JSON ที่อ่านได้")


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
        try:
            line_total = float(raw.get("line_total") or 0)
        except Exception:
            line_total = 0.0
        try:
            unit_price = float(raw.get("unit_price") or 0)
        except Exception:
            unit_price = 0.0
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


def _model_candidates() -> list[str]:
    configured = _secret("GEMINI_MODEL", "gemini-3.8-flash") or "gemini-3.8-flash"
    fallback_text = _secret("GEMINI_FALLBACK_MODELS", "") or ""
    configured_fallbacks = [m.strip() for m in fallback_text.split(",") if m.strip()]
    result: list[str] = []
    for model in [configured, *configured_fallbacks, *DEFAULT_MODELS]:
        if model not in result:
            result.append(model)
    return result


def _should_try_next_model(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "404",
            "not_found",
            "not found",
            "model is no longer available",
            "model not found",
            "unsupported model",
            "503",
            "unavailable",
            "high demand",
            "429",
            "resource_exhausted",
        )
    )


def parse_receipt_image(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    api_key = _secret("GEMINI_API_KEY") or _secret("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ยังไม่ได้ตั้งค่า GEMINI_API_KEY: local ให้ใส่ในไฟล์ .env; "
            "Streamlit Cloud ให้ใส่ใน Settings > Secrets"
        )

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "ไม่พบ Google GenAI SDK กรุณารัน: python -m pip install -r requirements.txt"
        ) from exc

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
- total คือยอดสุทธิบนใบเสร็จ
- ถ้าอ่านค่าไม่ได้ให้ใช้ 0 แทน อย่าเดาเกินข้อมูลในภาพ
""".strip()

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    inputs = [
        {"type": "image", "mime_type": mime_type, "data": image_b64},
        {"type": "text", "text": prompt},
    ]

    errors: list[str] = []
    for model in _model_candidates():
        try:
            interaction = client.interactions.create(model=model, input=inputs)
            text = getattr(interaction, "output_text", None)
            if not text:
                raise RuntimeError("Gemini ไม่ได้ส่งข้อความกลับมา")
            parsed = normalize_receipt(_extract_json(text))
            parsed["_model_used"] = model
            return parsed
        except Exception as exc:
            errors.append(f"{model}: {exc}")
            text = str(exc).lower()
            if any(marker in text for marker in ("503", "unavailable", "high demand", "429", "resource_exhausted")):
                time.sleep(1.2)
            if not _should_try_next_model(exc):
                raise RuntimeError(f"Gemini API error ({model}): {exc}") from exc

    short_errors = " | ".join(errors[-3:])
    raise RuntimeError(
        "ไม่พบ Gemini model ที่ใช้งานได้กับ API key นี้ ลองตั้ง GEMINI_MODEL เป็นโมเดลที่บัญชีเปิดให้ใช้ "
        f"รายละเอียดล่าสุด: {short_errors}"
    )
