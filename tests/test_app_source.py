from pathlib import Path


APP_SOURCE = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")


def test_payer_ui_removed():
    assert '"คนจ่ายก่อน"' not in APP_SOURCE
    assert "paid_totals" not in APP_SOURCE
    assert "settlements(" not in APP_SOURCE


def test_select_all_uses_safe_callback():
    assert "def select_all_consumers" in APP_SOURCE
    assert "on_click=select_all_consumers" in APP_SOURCE
    assert 'st.session_state[f"people_{item[\'id\']}"]' not in APP_SOURCE


def test_add_member_uses_callback():
    assert "on_click=add_member_from_input" in APP_SOURCE
