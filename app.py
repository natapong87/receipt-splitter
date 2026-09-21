from __future__ import annotations

import hashlib
import html
import json
import uuid

import streamlit as st

from billing import calculate_bill
from receipt_parser import parse_receipt_image
from share_card import build_share_card

st.set_page_config(page_title="Split Bill", page_icon="🧾", layout="centered", initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
:root { --blue:#397dcc; --soft:#f7f9fc; --line:#e9edf3; --text:#1c2430; --muted:#788292; }
[data-testid="stAppViewContainer"] { background:#fff; }
[data-testid="stMainBlockContainer"] {
  max-width:760px;
  padding-top:.45rem;
  padding-bottom:1.25rem;
}
header[data-testid="stHeader"] { height:0; min-height:0; background:transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none!important; }
#MainMenu, footer { visibility:hidden; }
.app-title {
  display:flex;
  align-items:center;
  gap:.45rem;
  font-size:1.15rem;
  font-weight:800;
  margin:0 0 .18rem;
  color:var(--text);
}
.logo-dot {
  width:27px;
  height:27px;
  border-radius:50%;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  background:#eaf3ff;
  color:#2766ad;
  font-size:15px;
}
.metric-row {
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:4px;
  margin:0 0 .28rem;
}
.metric-card { text-align:center; padding:3px 2px 4px; border-radius:9px; background:#fff; }
.metric-label { color:#9aa2ad; font-size:.69rem; line-height:1.15; margin-bottom:1px; white-space:nowrap; }
.metric-value { color:#20242a; font-weight:800; font-size:1.08rem; line-height:1.15; }
.section-label { font-size:.82rem; font-weight:800; color:#2c333d; margin:.3rem 0 .2rem; }
.expense-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
.expense-name { font-weight:800; font-size:1rem; color:#242a33; }
.expense-price { font-weight:800; font-size:1rem; white-space:nowrap; }
.muted { color:var(--muted); font-size:.78rem; }
.pills { margin-top:4px; display:flex; gap:5px; flex-wrap:wrap; }
.pill { display:inline-block; border-radius:7px; padding:2px 7px; font-size:.70rem; font-weight:700; color:#fff; background:#18866d; }
.unassigned-pill { background:#aab1bc; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line)!important; border-radius:12px!important; box-shadow:none!important; }
.stButton button, .stDownloadButton button { border-radius:8px; font-weight:700; }
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] { background:var(--blue); border-color:var(--blue); }

/* Destructive buttons: compact red buttons with white text/icons. */
[class*="st-key-remove_person_"] button,
[class*="st-key-del_"] button {
  background:#ef4444!important;
  border-color:#ef4444!important;
  color:#fff!important;
  box-shadow:none!important;
}
[class*="st-key-remove_person_"] button:hover,
[class*="st-key-del_"] button:hover {
  background:#dc2626!important;
  border-color:#dc2626!important;
  color:#fff!important;
}
[class*="st-key-remove_person_"] button:active,
[class*="st-key-del_"] button:active {
  background:#b91c1c!important;
  border-color:#b91c1c!important;
}

/* Expense editor: keep both editing rows on one line on mobile. */
[class*="st-key-expense_card_"] [data-testid="stHorizontalBlock"] {
  align-items:center!important;
}
[class*="st-key-expense_card_"] input {
  min-height:2.35rem!important;
}
[class*="st-key-expense_card_"] [data-baseweb="select"] > div {
  min-height:2.35rem!important;
}
[class*="st-key-expense_card_"] .stButton button {
  min-height:2.35rem!important;
  height:2.35rem!important;
  padding:.15rem .45rem!important;
  white-space:nowrap!important;
}
[class*="st-key-expense_card_"] [class*="st-key-del_"] button {
  width:2.35rem!important;
  min-width:2.35rem!important;
  padding:0!important;
  font-size:1.05rem!important;
}

/* Compact native segmented control: one row, three equal segments. */
.st-key-top_nav {
  width:100%;
  max-width:520px;
  margin:.05rem auto .35rem;
}
.st-key-top_nav [data-testid="stSegmentedControl"] { width:100%!important; }
.st-key-top_nav [role="radiogroup"] {
  display:flex!important;
  flex-wrap:nowrap!important;
  width:100%!important;
}
.st-key-top_nav [role="radio"] {
  flex:1 1 0!important;
  min-width:0!important;
  min-height:2.1rem!important;
  justify-content:center!important;
  padding:.18rem .3rem!important;
  font-size:.88rem!important;
  white-space:nowrap!important;
}

/* Compact member controls. */
.st-key-member_add input {
  min-height:2.25rem!important;
  height:2.25rem!important;
  overflow:hidden!important;
  resize:none!important;
}
.st-key-member_add [data-testid="stTextInput"] {
  overflow:visible!important;
  flex:1 1 auto!important;
  min-width:0!important;
}
.st-key-member_add .stButton button {
  min-height:2.25rem!important;
  height:2.25rem!important;
  padding:.15rem .75rem!important;
}

/*
Member rows use real Streamlit columns with wrap=False. The final column has a
fixed visual width so every delete button lines up on phones, regardless of the
member-name length or viewport width.
*/
.st-key-member_list,
.st-key-member_list > div,
.st-key-member_list [data-testid="stVerticalBlock"] {
  overflow:visible!important;
  max-height:none!important;
  height:auto!important;
}
.st-key-member_list [data-testid="stVerticalBlock"] { gap:0!important; }
[class*="st-key-member_row_"] {
  width:100%!important;
  min-height:38px!important;
  margin:0!important;
  padding:3px 0!important;
  border-bottom:1px solid var(--line)!important;
  overflow:visible!important;
  box-sizing:border-box!important;
}
[class*="st-key-member_row_"] > div,
[class*="st-key-member_row_"] [data-testid="stVerticalBlock"] {
  gap:0!important;
  margin:0!important;
  padding:0!important;
}
[class*="st-key-member_row_"] [data-testid="stHorizontalBlock"] {
  width:100%!important;
  min-height:32px!important;
  height:32px!important;
  align-items:center!important;
  flex-wrap:nowrap!important;
  gap:0!important;
  overflow:visible!important;
}
[class*="st-key-member_row_"] [data-testid="stColumn"] {
  min-width:0!important;
  height:32px!important;
  display:flex!important;
  align-items:center!important;
  padding:0!important;
  margin:0!important;
}
[class*="st-key-member_row_"] [data-testid="stColumn"]:first-child {
  flex:1 1 auto!important;
  width:auto!important;
}
[class*="st-key-member_row_"] [data-testid="stColumn"]:last-child {
  flex:0 0 38px!important;
  width:38px!important;
  min-width:38px!important;
  max-width:38px!important;
  justify-content:flex-end!important;
}
[class*="st-key-member_row_"] [data-testid="stMarkdownContainer"],
[class*="st-key-member_row_"] [data-testid="stMarkdownContainer"] p {
  width:100%!important;
  margin:0!important;
  padding:0!important;
}
.member-name {
  display:flex;
  align-items:center;
  width:100%;
  min-width:0;
  height:32px;
  margin:0;
  padding:0 .5rem 0 .15rem;
  font-weight:800;
  font-size:.93rem;
  color:var(--text);
  line-height:1.2;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
  box-sizing:border-box;
}
[class*="st-key-remove_person_"] {
  width:30px!important;
  min-width:30px!important;
  max-width:30px!important;
  height:30px!important;
  margin:0 0 0 auto!important;
  padding:0!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
}
[class*="st-key-remove_person_"] [data-testid="stButton"] {
  width:30px!important;
  height:30px!important;
  margin:0!important;
  padding:0!important;
}
[class*="st-key-remove_person_"] button {
  width:30px!important;
  min-width:30px!important;
  max-width:30px!important;
  height:30px!important;
  min-height:30px!important;
  max-height:30px!important;
  padding:0!important;
  margin:0!important;
  border-radius:7px!important;
  font-size:.9rem!important;
  line-height:1!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
}
.st-key-clear_members { margin-top:.15rem; text-align:center; }
.st-key-clear_members .stButton button {
  min-height:2rem!important;
  padding:.1rem .55rem!important;
  font-size:.82rem!important;
}
[data-testid="stMetric"] { background:var(--soft); padding:8px 10px; border-radius:10px; }

@media (max-width:640px) {
  [data-testid="stMainBlockContainer"] {
    padding-left:.62rem;
    padding-right:.62rem;
    padding-top:.22rem;
    padding-bottom:.75rem;
  }
  .app-title { font-size:1.08rem; margin-bottom:.1rem; }
  .logo-dot { width:25px; height:25px; font-size:14px; }
  .metric-row { margin-bottom:.18rem; }
  .metric-label { font-size:.66rem; }
  .metric-value { font-size:1rem; }
  .st-key-top_nav { margin-bottom:.25rem; }
  .section-label { margin-top:.2rem; }
}
</style>
""",
    unsafe_allow_html=True,
)


def init_state():
    defaults = {
        "people": ["A", "B", "C"],
        "expenses": [],
        "merchant": "",
        "service_charge": 0.0,
        "vat": 0.0,
        "discount": 0.0,
        "receipt_total": 0.0,
        "active_view": "สมาชิก",
        "receipt_hash": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Migrate sessions created by older versions that stored a payer per item.
    for expense in st.session_state.expenses:
        expense.pop("payer", None)


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def add_expense(name="รายการใหม่", price=0.0, consumers=None):
    st.session_state.expenses.append(
        {
            "id": new_id(),
            "name": str(name or "รายการใหม่"),
            "price": round(float(price or 0), 2),
            "people": list(consumers or []),
        }
    )


def expense_total() -> float:
    subtotal = sum(float(x.get("price", 0)) for x in st.session_state.expenses)
    return subtotal + float(st.session_state.service_charge) + float(st.session_state.vat) - float(st.session_state.discount)


def bill_result():
    return calculate_bill(
        st.session_state.expenses,
        st.session_state.people,
        service_charge=st.session_state.service_charge,
        vat=st.session_state.vat,
        discount=st.session_state.discount,
    )


def chips(names, css_class="pill"):
    if not names:
        return '<span class="pill unassigned-pill">ยังไม่เลือก</span>'
    return "".join(f'<span class="pill {css_class}">{html.escape(str(n))}</span>' for n in names)


def add_member_from_input():
    """Add a member before widgets are recreated on the next Streamlit rerun."""
    name = str(st.session_state.get("new_member", "")).strip()
    if name and name not in st.session_state.people:
        st.session_state.people.append(name)
    st.session_state["new_member"] = ""


def remove_member(person: str):
    """Remove a member and detach them from every expense before rerendering."""
    st.session_state.people = [p for p in st.session_state.people if p != person]
    for item in st.session_state.expenses:
        item["people"] = [p for p in item.get("people", []) if p != person]


def select_all_consumers(item_id: str):
    """Safely update a multiselect from a button callback.

    Streamlit does not allow changing a widget key after that widget has already
    been instantiated in the same run. A callback executes before the next run,
    so updating the multiselect state here avoids
    StreamlitWidgetAlreadyInstantiatedError.
    """
    selected = list(st.session_state.people)
    for expense in st.session_state.expenses:
        if expense.get("id") == item_id:
            expense["people"] = selected
            break
    st.session_state[f"people_{item_id}"] = selected


def import_receipt(parsed):
    st.session_state.merchant = parsed.get("merchant", "")
    st.session_state.service_charge = float(parsed.get("service_charge", 0) or 0)
    st.session_state.vat = float(parsed.get("vat", 0) or 0)
    st.session_state.discount = float(parsed.get("discount", 0) or 0)
    st.session_state.receipt_total = float(parsed.get("total", 0) or 0)
    st.session_state.expenses = []
    for row in parsed.get("items", []):
        qty = max(1, int(row.get("quantity", 1) or 1))
        unit = float(row.get("unit_price", 0) or 0)
        if unit <= 0:
            unit = float(row.get("line_total", 0) or 0) / qty
        base_name = str(row.get("name") or "รายการ")
        for n in range(1, qty + 1):
            name = f"{base_name} #{n}" if qty > 1 else base_name
            add_expense(name=name, price=unit)


init_state()

st.markdown('<div class="app-title"><span class="logo-dot">🧾</span><span>Split Bill</span></div>', unsafe_allow_html=True)

metric_html = f"""
<div class="metric-row">
  <div class="metric-card"><div class="metric-label">รายการ</div><div class="metric-value">{len(st.session_state.expenses)}</div></div>
  <div class="metric-card"><div class="metric-label">ยอดรวมทั้งหมด</div><div class="metric-value">{expense_total():,.0f}</div></div>
  <div class="metric-card"><div class="metric-label">สมาชิก</div><div class="metric-value">{len(st.session_state.people)}</div></div>
</div>
"""
st.markdown(metric_html, unsafe_allow_html=True)

with st.container(key="top_nav", gap=None):
    selected_view = st.segmented_control(
        "เมนูหลัก",
        options=["สมาชิก", "รายการ", "สรุป"],
        selection_mode="single",
        default=st.session_state.active_view,
        key="top_nav_choice",
        label_visibility="collapsed",
        width="stretch",
        wrap=False,
    )

view = selected_view or st.session_state.active_view
st.session_state.active_view = view

if view == "สมาชิก":
    st.markdown('<div class="section-label">สมาชิก</div>', unsafe_allow_html=True)

    with st.container(key="member_add", gap=None):
        add_col, btn_col = st.columns(
            [1, 0.22],
            gap="xsmall",
            vertical_alignment="center",
            wrap=False,
        )
        with add_col:
            new_member = st.text_input(
                "ชื่อสมาชิก",
                placeholder="เช่น Nat",
                label_visibility="collapsed",
                key="new_member",
                width="stretch",
            )
        with btn_col:
            st.button(
                "เพิ่ม",
                type="primary",
                width="stretch",
                key="add_member",
                on_click=add_member_from_input,
            )

    if not st.session_state.people:
        st.info("เพิ่มสมาชิกก่อนเริ่มหารบิล")

    with st.container(key="member_list", gap=None):
        for idx, person in enumerate(list(st.session_state.people)):
            with st.container(key=f"member_row_{idx}", gap=None):
                name_col, remove_col = st.columns(
                    [12, 1],
                    gap=None,
                    vertical_alignment="center",
                    wrap=False,
                )
                with name_col:
                    st.markdown(
                        f'<div class="member-name" title="{html.escape(person)}">{html.escape(person)}</div>',
                        unsafe_allow_html=True,
                    )
                with remove_col:
                    st.button(
                        "×",
                        key=f"remove_person_{idx}",
                        type="secondary",
                        width=30,
                        help=f"ลบ {person}",
                        on_click=remove_member,
                        args=(person,),
                    )

    if st.session_state.people:
        with st.container(key="clear_members", horizontal=True, horizontal_alignment="center", gap=None):
            if st.button("ล้างสมาชิกทั้งหมด", type="tertiary", width="content"):
                st.session_state.people = []
                for item in st.session_state.expenses:
                    item["people"] = []
                st.rerun()

elif view == "รายการ":
    st.markdown('<div class="section-label">รายการ</div>', unsafe_allow_html=True)

    with st.expander("📷 สแกนใบเสร็จด้วย Gemini", expanded=not st.session_state.expenses):
        merchant = st.text_input("ชื่อร้าน", value=st.session_state.merchant, placeholder="ชื่อร้าน (ถ้ามี)")
        st.session_state.merchant = merchant
        uploaded = st.file_uploader(
            "อัปโหลดรูปใบเสร็จ JPG / PNG",
            type=["jpg", "jpeg", "png"],
            key="receipt_upload",
        )
        image_file = uploaded
        if image_file:
            image_bytes = image_file.getvalue()
            file_hash = hashlib.sha256(image_bytes).hexdigest()
            st.image(image_bytes, use_container_width=True)
            if st.button("✨ อ่านใบเสร็จและสร้างรายการ", type="primary", use_container_width=True):
                try:
                    with st.spinner("กำลังอ่านใบเสร็จ..."):
                        parsed = parse_receipt_image(image_bytes, image_file.type or "image/jpeg")
                    import_receipt(parsed)
                    st.session_state.receipt_hash = file_hash
                    st.success(f"อ่านสำเร็จด้วย {parsed.get('_model_used', 'Gemini')}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"อ่านใบเสร็จไม่สำเร็จ: {exc}")

        f1, f2, f3, f4 = st.columns(4)
        st.session_state.service_charge = f1.number_input("Service", min_value=0.0, value=float(st.session_state.service_charge), step=1.0)
        st.session_state.vat = f2.number_input("VAT", min_value=0.0, value=float(st.session_state.vat), step=1.0)
        st.session_state.discount = f3.number_input("Discount", min_value=0.0, value=float(st.session_state.discount), step=1.0)
        st.session_state.receipt_total = f4.number_input("Receipt total", min_value=0.0, value=float(st.session_state.receipt_total), step=1.0)

    if not st.session_state.expenses:
        st.info("ยังไม่มีรายการ กด Add expense หรือสแกนใบเสร็จด้านบน")

    for idx, item in enumerate(list(st.session_state.expenses)):
        with st.container(border=True, key=f"expense_card_{item['id']}", gap="small"):
            # Row 1: menu name + price + compact delete button.
            name_col, price_col, delete_col = st.columns(
                [2.55, 1.05, 0.42],
                gap="xsmall",
                vertical_alignment="center",
                wrap=False,
            )
            with name_col:
                new_name = st.text_input(
                    "ชื่อเมนู",
                    value=item.get("name", ""),
                    key=f"name_{item['id']}",
                    label_visibility="collapsed",
                    placeholder="ชื่อเมนู",
                    width="stretch",
                )
            with price_col:
                new_price = st.number_input(
                    "ราคา",
                    min_value=0.0,
                    value=float(item.get("price", 0)),
                    step=1.0,
                    key=f"price_{item['id']}",
                    label_visibility="collapsed",
                    width="stretch",
                )
            with delete_col:
                delete_clicked = st.button(
                    "×",
                    key=f"del_{item['id']}",
                    type="secondary",
                    width="stretch",
                    help="ลบรายการ",
                )

            item["name"] = new_name
            item["price"] = new_price

            if delete_clicked:
                st.session_state.expenses = [x for x in st.session_state.expenses if x["id"] != item["id"]]
                st.rerun()

            # Row 2: who shares this item + select-all button.
            people_col, all_col = st.columns(
                [2.35, 1.0],
                gap="xsmall",
                vertical_alignment="center",
                wrap=False,
            )
            with people_col:
                selected = st.multiselect(
                    "หารกัน",
                    st.session_state.people,
                    default=[p for p in item.get("people", []) if p in st.session_state.people],
                    key=f"people_{item['id']}",
                    placeholder="หารกัน",
                    label_visibility="collapsed",
                    width="stretch",
                )
            item["people"] = selected

            with all_col:
                st.button(
                    "เลือกทุกคน",
                    key=f"all_{item['id']}",
                    width="stretch",
                    on_click=select_all_consumers,
                    args=(item["id"],),
                )

    if st.button("＋ เพิ่มรายการ", type="primary", use_container_width=True):
        add_expense(consumers=list(st.session_state.people))
        st.rerun()

    if st.session_state.expenses:
        if st.button("ล้างรายการทั้งหมด", use_container_width=True):
            st.session_state.expenses = []
            st.rerun()

else:
    st.markdown('<div class="section-label">สรุป</div>', unsafe_allow_html=True)
    if not st.session_state.expenses:
        st.info("ยังไม่มีรายการสำหรับสรุป")
    else:
        result = bill_result()
        owed = {p: float(result["totals"].get(p, 0)) for p in st.session_state.people}

        if result["unassigned"]:
            st.warning(f"มี {len(result['unassigned'])} รายการที่ยังไม่ได้เลือกคนหาร จึงยังไม่ถูกรวมในยอดของสมาชิก")

        for p in st.session_state.people:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1], vertical_alignment="center", wrap=False)
                c1.markdown(f"**{html.escape(p)}**")
                c2.markdown(f"**{owed[p]:,.2f} บาท**")

        allocated_total = sum(owed.values())
        m1, m2, m3 = st.columns(3)
        m1.metric("แบ่งแล้ว", f"{allocated_total:,.2f}")
        m2.metric("ใบเสร็จ", f"{float(st.session_state.receipt_total):,.2f}")
        receipt = float(st.session_state.receipt_total)
        m3.metric("ส่วนต่าง", f"{allocated_total - receipt:,.2f}" if receipt else "-")

        st.markdown("#### 📤 แชร์สรุป")
        st.caption("ภาพ PNG ใช้ภาษาอังกฤษเพื่อให้ตัวอักษรแสดงได้ถูกต้องบนทุกอุปกรณ์")
        share_png = build_share_card(
            merchant=st.session_state.merchant,
            people=st.session_state.people,
            totals=owed,
            calculated_total=allocated_total,
            receipt_total=float(st.session_state.receipt_total),
            items=st.session_state.expenses,
        )
        st.image(share_png, use_container_width=True)
        st.download_button(
            "📸 บันทึกภาพสรุปภาษาอังกฤษ (.png)",
            data=share_png,
            file_name="bill_summary.png",
            mime="image/png",
            type="primary",
            use_container_width=True,
        )

        export = {
            "merchant": st.session_state.merchant,
            "members": st.session_state.people,
            "expenses": st.session_state.expenses,
            "summary": {p: {"amount": owed[p]} for p in st.session_state.people},
        }
        st.download_button(
            "ดาวน์โหลดข้อมูล (.json)",
            data=json.dumps(export, ensure_ascii=False, indent=2),
            file_name="bill_split_result.json",
            mime="application/json",
            use_container_width=True,
        )
