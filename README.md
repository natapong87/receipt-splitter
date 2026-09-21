# Split Bill — mobile-first edition

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

- Mobile-first layout แบบ Member / Expense / Summary
- Top metrics: จำนวนรายการ / ยอดรวม / จำนวนสมาชิก
- สแกนใบเสร็จด้วย Gemini
- รายการ x2/x3 ถูกแยกเป็นคนละรายการ
- เลือกคนหารและคนที่จ่ายก่อน
- คำนวณค่า Service / VAT / Discount ตามสัดส่วน
- คำนวณยอดสุทธิและวิธีโอนคืน
- บันทึกภาพสรุป PNG ภาษาไทย
