from __future__ import annotations

import hashlib
import html
import json
import uuid

import pandas as pd
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
[data-testid="stMainBlockContainer"] { max-width:760px; padding-top:1.2rem; padding-bottom:6rem; }
header[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer { visibility:hidden; }
.app-title { display:flex; align-items:center; gap:.55rem; font-size:1.28rem; font-weight:800; margin:.1rem 0 .65rem; color:var(--text); }
.logo-dot { width:30px; height:30px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; background:#eaf3ff; color:#2766ad; font-size:17px; }
.metric-row { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:6px 0 12px; }
.metric-card { text-align:center; padding:10px 6px 8px; border-radius:12px; background:#fff; }
.metric-label { color:#9aa2ad; font-size:.76rem; margin-bottom:4px; }
.metric-value { color:#20242a; font-weight:800; font-size:1.35rem; }
.section-label { font-size:.82rem; font-weight:800; color:#2c333d; margin:10px 0 4px; }
.expense-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
.expense-name { font-weight:800; font-size:1rem; color:#242a33; }
.expense-price { font-weight:800; font-size:1rem; white-space:nowrap; }
.muted { color:var(--muted); font-size:.78rem; }
.pills { margin-top:4px; display:flex; gap:5px; flex-wrap:wrap; }
.pill { display:inline-block; border-radius:7px; padding:2px 7px; font-size:.70rem; font-weight:700; color:#fff; background:#18866d; }
.payer-pill { background:#488d19; }
.unassigned-pill { background:#aab1bc; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line)!important; border-radius:12px!important; box-shadow:none!important; }
.stButton button, .stDownloadButton button { border-radius:8px; font-weight:700; }
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] { background:var(--blue); border-color:var(--blue); }
/* Keep the 3 navigation choices centered on desktop and mobile. */
div[data-testid="stRadio"] {
  width:100% !important;
  display:flex !important;
  justify-content:center !important;
  margin:0 auto 16px !important;
  padding:0 0 10px !important;
  border-bottom:1px solid var(--line);
}
div[data-testid="stRadio"] > div,
div[data-testid="stRadio"] div[role="radiogroup"] {
  width:min(100%, 520px) !important;
  display:grid !important;
  grid-template-columns:repeat(3, minmax(0, 1fr)) !important;
  gap:12px !important;
  margin:0 auto !important;
  justify-content:center !important;
}
div[data-testid="stRadio"] label {
  width:100% !important;
  display:flex !important;
  justify-content:center !important;
  align-items:center !important;
  gap:6px !important;
  padding:8px 6px 10px !important;
  margin:0 !important;
  text-align:center !important;
}
.member-row-marker { display:none; }
.member-name {
  font-weight:800;
  font-size:1rem;
  color:var(--text);
  padding:.35rem .1rem;
  line-height:2.1rem;
}
/* Member rows must stay A | X instead of stacking on narrow phones. */
div[data-testid="stVerticalBlock"]:has(.member-row-marker) div[data-testid="stHorizontalBlock"] {
  display:grid !important;
  grid-template-columns:minmax(0, 1fr) 48px !important;
  gap:8px !important;
  align-items:center !important;
  flex-wrap:nowrap !important;
}
div[data-testid="stVerticalBlock"]:has(.member-row-marker) div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
  width:auto !important;
  min-width:0 !important;
  flex:unset !important;
}
.member-divider {
  height:1px;
  background:var(--line);
  margin:1px 0 4px;
}
@media (max-width: 640px) {
  div[data-testid="stRadio"] { padding-left:10px !important; padding-right:10px !important; }
  div[data-testid="stRadio"] > div,
  div[data-testid="stRadio"] div[role="radiogroup"] { gap:6px !important; width:100% !important; }
}
[data-testid="stMetric"] { background:var(--soft); padding:10px 12px; border-radius:10px; }
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding-left:.8rem; padding-right:.8rem; padding-top:.65rem; }
  .metric-value { font-size:1.18rem; }
  .metric-card { padding:8px 2px; }
  div[data-testid="column"] { min-width:0!important; }
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


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def add_expense(name="รายการใหม่", price=0.0, consumers=None, payer=""):
    st.session_state.expenses.append(
        {
            "id": new_id(),
            "name": str(name or "รายการใหม่"),
            "price": round(float(price or 0), 2),
            "people": list(consumers or []),
            "payer": payer or "",
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


def paid_totals() -> dict[str, float]:
    paid = {p: 0.0 for p in st.session_state.people}
    for item in st.session_state.expenses:
        payer = item.get("payer")
        if payer in paid:
            paid[payer] += float(item.get("price", 0))
    # Extra charges are treated as not prepaid because receipt rarely identifies who paid them.
    return paid


def settlements(net: dict[str, float]):
    creditors = [[p, v] for p, v in net.items() if v > 0.005]
    debtors = [[p, -v] for p, v in net.items() if v < -0.005]
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    out = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i][1], creditors[j][1])
        if amount > 0.005:
            out.append((debtors[i][0], creditors[j][0], round(amount, 2)))
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] < 0.005:
            i += 1
        if creditors[j][1] < 0.005:
            j += 1
    return out


def chips(names, css_class="pill"):
    if not names:
        return '<span class="pill unassigned-pill">ยังไม่เลือก</span>'
    return "".join(f'<span class="pill {css_class}">{html.escape(str(n))}</span>' for n in names)


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

view = st.radio(
    "Navigation",
    ["สมาชิก", "รายการ", "สรุป"],
    horizontal=True,
    label_visibility="collapsed",
    key="active_view",
)

if view == "สมาชิก":
    st.markdown('<div class="section-label">สมาชิก</div>', unsafe_allow_html=True)
    add_col, btn_col = st.columns([4, 1])
    with add_col:
        new_member = st.text_input("ชื่อสมาชิก", placeholder="เช่น Nat", label_visibility="collapsed", key="new_member")
    with btn_col:
        if st.button("เพิ่ม", type="primary", use_container_width=True):
            name = new_member.strip()
            if name and name not in st.session_state.people:
                st.session_state.people.append(name)
                st.session_state.new_member = ""
                st.rerun()

    if not st.session_state.people:
        st.info("เพิ่มสมาชิกก่อนเริ่มหารบิล")
    st.markdown('<div class="member-row-marker"></div>', unsafe_allow_html=True)
    for idx, person in enumerate(list(st.session_state.people)):
        c1, c2 = st.columns([8, 1], vertical_alignment="center")
        c1.markdown(f'<div class="member-name">{html.escape(person)}</div>', unsafe_allow_html=True)
        if c2.button("✕", key=f"remove_person_{idx}", use_container_width=True):
            st.session_state.people.remove(person)
            for item in st.session_state.expenses:
                item["people"] = [p for p in item.get("people", []) if p != person]
                if item.get("payer") == person:
                    item["payer"] = ""
            st.rerun()
        st.markdown('<div class="member-divider"></div>', unsafe_allow_html=True)

    if st.session_state.people and st.button("ล้างสมาชิกทั้งหมด", use_container_width=True):
        st.session_state.people = []
        for item in st.session_state.expenses:
            item["people"] = []
            item["payer"] = ""
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
        with st.container(border=True):
            top_left, top_right = st.columns([4, 1.2])
            with top_left:
                st.markdown(
                    f'<div class="expense-head"><div><div class="expense-name">{html.escape(item.get("name", "รายการ"))}</div>'
                    f'<div class="pills">{chips(item.get("people", []))}</div></div></div>',
                    unsafe_allow_html=True,
                )
            with top_right:
                st.markdown(f'<div class="expense-price">{float(item.get("price",0)):,.2f}</div>', unsafe_allow_html=True)

            e1, e2 = st.columns([3, 1.3])
            new_name = e1.text_input("รายการ", value=item.get("name", ""), key=f"name_{item['id']}", label_visibility="collapsed")
            new_price = e2.number_input("ราคา", min_value=0.0, value=float(item.get("price", 0)), step=1.0, key=f"price_{item['id']}", label_visibility="collapsed")
            item["name"] = new_name
            item["price"] = new_price

            selected = st.multiselect(
                "หารกับ",
                st.session_state.people,
                default=[p for p in item.get("people", []) if p in st.session_state.people],
                key=f"people_{item['id']}",
                placeholder="เลือกคนที่กิน/ใช้รายการนี้",
            )
            item["people"] = selected

            payer_options = ["ยังไม่ระบุ", *st.session_state.people]
            current_payer = item.get("payer") if item.get("payer") in st.session_state.people else "ยังไม่ระบุ"
            payer = st.selectbox(
                "คนจ่ายก่อน",
                payer_options,
                index=payer_options.index(current_payer),
                key=f"payer_{item['id']}",
            )
            item["payer"] = "" if payer == "ยังไม่ระบุ" else payer

            c_all, c_del = st.columns([3, 1])
            if c_all.button("เลือกทุกคน", key=f"all_{item['id']}", use_container_width=True):
                item["people"] = list(st.session_state.people)
                st.session_state[f"people_{item['id']}"] = list(st.session_state.people)
                st.rerun()
            if c_del.button("ลบ", key=f"del_{item['id']}", use_container_width=True):
                st.session_state.expenses = [x for x in st.session_state.expenses if x["id"] != item["id"]]
                st.rerun()

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
        paid = paid_totals()
        owed = {p: float(result["totals"].get(p, 0)) for p in st.session_state.people}
        net = {p: round(paid.get(p, 0) - owed.get(p, 0), 2) for p in st.session_state.people}

        if result["unassigned"]:
            st.warning(f"มี {len(result['unassigned'])} รายการที่ยังไม่ได้เลือกคนหาร จึงยังไม่ถูกรวมในยอดของสมาชิก")

        for p in st.session_state.people:
            with st.container(border=True):
                c1, c2 = st.columns([2, 3])
                c1.markdown(f"**{html.escape(p)}**")
                c2.markdown(
                    f"ต้องรับผิดชอบ **{owed[p]:,.2f}** · จ่ายไป **{paid[p]:,.2f}** · สุทธิ **{net[p]:+,.2f}**"
                )

        transfers = settlements(net)
        if transfers:
            st.markdown("#### 💸 วิธีเคลียร์เงิน")
            for sender, receiver, amount in transfers:
                st.markdown(f"**{html.escape(sender)} → {html.escape(receiver)} : {amount:,.2f} บาท**")
        elif any(paid.values()):
            st.success("ยอดที่ระบุผู้จ่ายสมดุลแล้ว")
        else:
            st.caption("ยังไม่ได้ระบุคนจ่ายก่อนในแต่ละรายการ จึงยังคำนวณการโอนคืนไม่ได้")

        allocated_total = sum(owed.values())
        m1, m2, m3 = st.columns(3)
        m1.metric("แบ่งแล้ว", f"{allocated_total:,.2f}")
        m2.metric("ใบเสร็จ", f"{float(st.session_state.receipt_total):,.2f}")
        receipt = float(st.session_state.receipt_total)
        m3.metric("ส่วนต่าง", f"{allocated_total - receipt:,.2f}" if receipt else "-")

        st.markdown("#### 📤 แชร์สรุป")
        share_png = build_share_card(
            merchant=st.session_state.merchant,
            people=st.session_state.people,
            totals=owed,
            calculated_total=allocated_total,
            receipt_total=float(st.session_state.receipt_total),
            items=st.session_state.expenses,
            paid=paid,
            net=net,
            settlements=transfers,
        )
        st.image(share_png, use_container_width=True)
        st.download_button(
            "📸 บันทึกภาพสรุป (.png)",
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
            "summary": {p: {"owed": owed[p], "paid": paid[p], "net": net[p]} for p in st.session_state.people},
            "settlements": transfers,
        }
        st.download_button(
            "ดาวน์โหลดข้อมูล (.json)",
            data=json.dumps(export, ensure_ascii=False, indent=2),
            file_name="bill_split_result.json",
            mime="application/json",
            use_container_width=True,
        )
