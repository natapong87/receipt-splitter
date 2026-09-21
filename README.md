# Split Bill — mobile-first edition v8

เว็บหารบิลสำหรับมือถือ: สมาชิก / รายการ / สรุปยอด พร้อมสแกนใบเสร็จด้วย Google Gemini และดาวน์โหลดภาพสรุปภาษาไทยเป็น PNG

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run app.py
```

`.env`

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
```

## Streamlit Community Cloud

อัปโหลดไฟล์ทั้งหมดในโปรเจกต์ รวม `packages.txt` แต่ **อย่าอัปโหลด `.env`**

ตั้ง Secrets:

```toml
GEMINI_API_KEY = "your_key_here"
GEMINI_MODEL = "gemini-3.8-flash"
```

`packages.txt` จะติดตั้งฟอนต์ภาษาไทยบน Linux เพื่อให้ภาพ PNG ที่ดาวน์โหลดอ่านภาษาไทยได้ถูกต้อง

## Main features

- Mobile-first layout แบบ สมาชิก / รายการ / สรุป
- Top metrics: จำนวนรายการ / ยอดรวม / จำนวนสมาชิก
- สแกนใบเสร็จด้วย Gemini
- รายการ x2/x3 ถูกแยกเป็นคนละรายการ
- เลือกคนหารและคนที่จ่ายก่อน
- คำนวณค่า Service / VAT / Discount ตามสัดส่วน
- คำนวณยอดสุทธิและวิธีโอนคืน
- บันทึกภาพสรุป PNG ภาษาไทย

## UI v4

- จัดแถบ `สมาชิก | รายการ | สรุป` ให้อยู่กึ่งกลางหน้าจอและมีระยะขอบเท่ากันบนมือถือ
- ปรับหน้าสมาชิกให้เป็นแถวกะทัดรัด `ชื่อสมาชิก   ✕` เพื่อลดพื้นที่แนวตั้ง
- หน้าเริ่มต้นเปิดที่แท็บ `สมาชิก`


## v6
- เปลี่ยน navigation จาก radio เป็นปุ่ม 3 ช่องจริง เพื่อไม่ให้ข้อความตัดแนวตั้งบน iPhone
- จัดปุ่ม สมาชิก / รายการ / สรุป ให้อยู่กึ่งกลางและกว้างเท่ากัน
- ปรับรายชื่อสมาชิกเป็นแถวกะทัดรัด ชื่อซ้าย ปุ่มลบขวา
- คงข้อความ ยอดรวมทั้งหมด ในสรุปด้านบน

## v7 mobile layout fix
- Navigation uses three real Streamlit buttons in one forced no-wrap row on mobile.
- Member add form stays in one row.
- Member delete button stays on the same row as the member name on iPhone/Safari.
- Top metric uses the Thai label `ยอดรวมทั้งหมด`.


## v8 compact single-screen mobile layout
- เปลี่ยนเมนูเป็น `st.segmented_control` แบบกะทัดรัด 3 ช่องในบรรทัดเดียว
- บังคับแถวเพิ่มสมาชิกและแถวลบสมาชิกด้วย `wrap=False` เพื่อไม่ให้ปุ่มตกบรรทัดบน iPhone
- ลดความสูงของหัวเว็บ ตัวเลขสรุป เมนู และรายชื่อสมาชิก เพื่อให้สมาชิกเริ่มต้น 3 คนแสดงในหน้าจอเดียวได้มากขึ้น
- ซ่อนแถบเครื่องมือ Streamlit บนหน้าแอปเพื่อลดพื้นที่แนวตั้ง
- ต้องใช้ Streamlit 1.64 ขึ้นไป
