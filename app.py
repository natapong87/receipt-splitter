from __future__ import annotations

from decimal import Decimal
import hashlib
import json

import pandas as pd
import streamlit as st

from billing import calculate_bill
from receipt_parser import parse_receipt_image


st.set_page_config(page_title='หารบิลจากใบเสร็จ', page_icon='🧾', layout='wide')
st.title('🧾 หารบิลจากใบเสร็จ')
st.caption('อ่านใบเสร็จด้วย Google Gemini → ตรวจรายการ → แยกของที่สั่งซ้ำ → ระบุว่าใครกิน → คำนวณยอด')


def reset_after_receipt_change():
    for key in ['receipt_data', 'instances', 'calc_result', 'source_hash']:
        st.session_state.pop(key, None)


def expand_items(items):
    expanded = []
    for row in items:
        qty = max(1, int(row.get('quantity', 1)))
        unit = float(row.get('unit_price', 0))
        for n in range(1, qty + 1):
            expanded.append({
                'instance_id': f"{int(row.get('line_id', 0))}-{n}",
                'name': str(row.get('name', 'รายการ')),
                'occurrence': n,
                'label': f"{row.get('name', 'รายการ')} #{n}" if qty > 1 else str(row.get('name', 'รายการ')),
                'price': round(unit, 2),
                'people': [],
            })
    return expanded


with st.sidebar:
    st.header('👥 คนในมื้อนี้')
    names_text = st.text_area('ใส่ชื่อ คั่นด้วย comma หรือขึ้นบรรทัดใหม่', value='A, B, C', height=100)
    people = []
    for token in names_text.replace('\n', ',').split(','):
        token = token.strip()
        if token and token not in people:
            people.append(token)
    st.caption(f'{len(people)} คน: ' + ', '.join(people))
    if st.button('เริ่มมื้อใหม่', use_container_width=True):
        reset_after_receipt_change()
        st.rerun()

st.subheader('1) เพิ่มใบเสร็จ')
col_upload, col_camera = st.columns(2)
with col_upload:
    uploaded = st.file_uploader('อัปโหลด JPG / PNG', type=['jpg', 'jpeg', 'png'])
with col_camera:
    camera = st.camera_input('หรือถ่ายรูปใบเสร็จ')

image_file = camera or uploaded
if image_file:
    image_bytes = image_file.getvalue()
    source_hash = hashlib.sha256(image_bytes).hexdigest()
    if st.session_state.get('source_hash') not in (None, source_hash):
        reset_after_receipt_change()
    st.session_state.source_hash = source_hash

    left, right = st.columns([1, 1])
    with left:
        st.image(image_bytes, caption='ภาพใบเสร็จ', use_container_width=True)
    with right:
        st.info('กดอ่านด้วย Google Gemini แล้วตรวจแก้ชื่อ จำนวน และราคาก่อนหารบิล')
        if st.button('✨ อ่านใบเสร็จด้วย AI', type='primary', use_container_width=True):
            try:
                with st.spinner('กำลังอ่านใบเสร็จ...'):
                    parsed = parse_receipt_image(image_bytes, image_file.type or 'image/jpeg')
                st.session_state.receipt_data = parsed
                st.session_state.instances = None
                st.session_state.calc_result = None
                st.success('อ่านใบเสร็จแล้ว กรุณาตรวจข้อมูลด้านล่าง')
            except Exception as e:
                st.error(f'อ่านใบเสร็จไม่สำเร็จ: {e}')

st.divider()
st.subheader('2) ตรวจและแก้รายการ')

if 'receipt_data' not in st.session_state:
    if st.button('ใช้โหมดกรอกเอง (ไม่ใช้ AI)'):
        st.session_state.receipt_data = {
            'merchant': '',
            'items': [{'line_id': 1, 'name': 'รายการตัวอย่าง', 'quantity': 1, 'unit_price': 100.0, 'line_total': 100.0}],
            'service_charge': 0.0, 'vat': 0.0, 'discount': 0.0, 'total': 100.0,
        }
        st.rerun()
else:
    data = st.session_state.receipt_data
    merchant = st.text_input('ชื่อร้าน', value=data.get('merchant', ''))

    items_df = pd.DataFrame(data.get('items', []))
    if items_df.empty:
        items_df = pd.DataFrame([{'line_id': 1, 'name': '', 'quantity': 1, 'unit_price': 0.0, 'line_total': 0.0}])

    edited = st.data_editor(
        items_df,
        num_rows='dynamic',
        hide_index=True,
        use_container_width=True,
        column_config={
            'line_id': st.column_config.NumberColumn('ลำดับ', disabled=True),
            'name': st.column_config.TextColumn('เมนู', required=True),
            'quantity': st.column_config.NumberColumn('จำนวน', min_value=1, step=1, required=True),
            'unit_price': st.column_config.NumberColumn('ราคาต่อชิ้น', min_value=0.0, step=1.0, format='%.2f'),
            'line_total': st.column_config.NumberColumn('รวมบรรทัด', min_value=0.0, step=1.0, format='%.2f'),
        },
        disabled=['line_id'],
        key='items_editor',
    )

    fee_cols = st.columns(4)
    with fee_cols[0]:
        service = st.number_input('Service charge', min_value=0.0, value=float(data.get('service_charge', 0)), step=1.0)
    with fee_cols[1]:
        vat = st.number_input('VAT', min_value=0.0, value=float(data.get('vat', 0)), step=1.0)
    with fee_cols[2]:
        discount = st.number_input('ส่วนลด', min_value=0.0, value=float(data.get('discount', 0)), step=1.0)
    with fee_cols[3]:
        receipt_total = st.number_input('ยอดรวมบนใบเสร็จ', min_value=0.0, value=float(data.get('total', 0)), step=1.0)

    if st.button('ยืนยันรายการและแยกตามจำนวน', type='primary'):
        normalized = []
        for i, row in edited.reset_index(drop=True).iterrows():
            qty = max(1, int(row.get('quantity') or 1))
            unit = float(row.get('unit_price') or 0)
            line = float(row.get('line_total') or 0)
            if unit <= 0 and line > 0:
                unit = line / qty
            if line <= 0 and unit > 0:
                line = unit * qty
            normalized.append({
                'line_id': i + 1,
                'name': str(row.get('name') or f'รายการ {i+1}'),
                'quantity': qty,
                'unit_price': round(unit, 2),
                'line_total': round(line, 2),
            })
        st.session_state.receipt_data = {
            'merchant': merchant,
            'items': normalized,
            'service_charge': service,
            'vat': vat,
            'discount': discount,
            'total': receipt_total,
        }
        st.session_state.instances = expand_items(normalized)
        st.session_state.calc_result = None
        st.rerun()

if st.session_state.get('instances') is not None:
    st.divider()
    st.subheader('3) ระบุว่าใครกินรายการไหน')
    st.caption('ถ้าเมนูเดียวกันสั่ง 2 จาน ระบบจะแยกเป็น #1 และ #2 ให้เลือกคนกินคนละชุดได้')

    instances = st.session_state.instances
    select_all = st.checkbox('เลือกทุกคนเป็นค่าเริ่มต้นสำหรับรายการที่ยังไม่ได้เลือก', value=False)

    for idx, item in enumerate(instances):
        cols = st.columns([3, 1, 4])
        with cols[0]:
            st.write(f"**{item['label']}**")
        with cols[1]:
            st.write(f"{item['price']:,.2f} บาท")
        with cols[2]:
            default_people = item.get('people') or (people if select_all else [])
            chosen = st.multiselect(
                f"คนที่กิน {item['label']}",
                people,
                default=[p for p in default_people if p in people],
                key=f"consumers_{item['instance_id']}",
                label_visibility='collapsed',
                placeholder='เลือกคนที่กิน',
            )
            item['people'] = chosen
    st.session_state.instances = instances

    if st.button('💰 คำนวณยอด', type='primary', use_container_width=True):
        if not people:
            st.error('กรุณาใส่ชื่ออย่างน้อย 1 คน')
        else:
            d = st.session_state.receipt_data
            result = calculate_bill(
                instances,
                people,
                service_charge=d.get('service_charge', 0),
                vat=d.get('vat', 0),
                discount=d.get('discount', 0),
            )
            st.session_state.calc_result = result

if st.session_state.get('calc_result'):
    result = st.session_state.calc_result
    d = st.session_state.receipt_data
    st.divider()
    st.subheader('4) สรุปยอด')

    if result['unassigned']:
        st.warning(f"ยังมี {len(result['unassigned'])} รายการที่ยังไม่ได้ระบุคนกิน รายการเหล่านี้ยังไม่ถูกคิดเงิน")

    summary_rows = []
    for p in people:
        summary_rows.append({
            'ชื่อ': p,
            'ค่าอาหาร': float(result['food'][p]),
            'Service': float(result['service'][p]),
            'VAT': float(result['vat'][p]),
            'ส่วนลด': float(result['discount'][p]),
            'ต้องจ่าย': float(result['totals'][p]),
        })
    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(
        summary_df,
        hide_index=True,
        use_container_width=True,
        column_config={c: st.column_config.NumberColumn(c, format='%.2f บาท') for c in summary_df.columns if c != 'ชื่อ'},
    )

    calculated_total = sum(float(v) for v in result['totals'].values())
    m1, m2, m3 = st.columns(3)
    m1.metric('รวมที่จัดสรรแล้ว', f'{calculated_total:,.2f} บาท')
    m2.metric('ยอดบนใบเสร็จ', f"{float(d.get('total', 0)):,.2f} บาท")
    diff = calculated_total - float(d.get('total', 0) or 0)
    m3.metric('ส่วนต่าง', f'{diff:,.2f} บาท')

    for p in people:
        with st.expander(f"{p} — {float(result['totals'][p]):,.2f} บาท"):
            for detail in result['details'][p]:
                st.write(f"• {detail['item']}: {float(detail['amount']):,.2f} บาท")
            if float(result['service'][p]):
                st.write(f"• Service: {float(result['service'][p]):,.2f} บาท")
            if float(result['vat'][p]):
                st.write(f"• VAT: {float(result['vat'][p]):,.2f} บาท")
            if float(result['discount'][p]):
                st.write(f"• ส่วนลด: -{float(result['discount'][p]):,.2f} บาท")

    export = {
        'merchant': d.get('merchant', ''),
        'people': people,
        'items': [
            {'name': i['label'], 'price': i['price'], 'people': i.get('people', [])}
            for i in st.session_state.instances
        ],
        'summary': {p: float(result['totals'][p]) for p in people},
    }
    st.download_button(
        'ดาวน์โหลดผลลัพธ์ JSON',
        data=json.dumps(export, ensure_ascii=False, indent=2),
        file_name='bill_split_result.json',
        mime='application/json',
    )
