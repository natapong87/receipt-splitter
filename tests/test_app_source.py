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


def test_mobile_compact_expense_rows_and_red_delete_buttons():
    assert 'expense_card_' in APP_SOURCE
    assert 'name_col, price_col, delete_col = st.columns' in APP_SOURCE
    assert 'people_col, all_col = st.columns' in APP_SOURCE
    assert APP_SOURCE.count('wrap=False') >= 5
    assert '[class*="st-key-remove_person_"] button' in APP_SOURCE
    assert '[class*="st-key-del_"] button' in APP_SOURCE
    assert 'background:#ef4444!important' in APP_SOURCE
    assert 'color:#fff!important' in APP_SOURCE


def test_member_rows_use_fixed_delete_column_and_callback():
    assert 'name_col, remove_col = st.columns' in APP_SOURCE
    assert '[12, 1]' in APP_SOURCE
    assert 'vertical_alignment="center"' in APP_SOURCE
    assert 'on_click=remove_member' in APP_SOURCE
    assert 'width=30' in APP_SOURCE
    assert 'flex:0 0 38px!important' in APP_SOURCE
    assert 'text-overflow:ellipsis' in APP_SOURCE
