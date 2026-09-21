from receipt_parser import normalize_receipt, _extract_json, _model_candidates


def test_normalize_quantity_and_price():
    data = {
        "merchant": "ร้าน",
        "items": [{"name": "กะเพรา", "quantity": 2, "line_total": 200}],
        "total": 200,
    }
    out = normalize_receipt(data)
    assert out["items"][0]["quantity"] == 2
    assert out["items"][0]["unit_price"] == 100.0


def test_extract_json_from_code_fence():
    out = _extract_json('```json\n{"total": 100}\n```')
    assert out["total"] == 100


def test_default_model_is_current_flash(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)
    models = _model_candidates()
    assert models[0] == "gemini-3.8-flash"
    assert "gemini-3.6-flash" in models
