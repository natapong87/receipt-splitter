# Receipt Splitter — Google Gemini Edition

เว็บแอป Streamlit สำหรับอ่านใบเสร็จร้านอาหารด้วย **Google Gemini API** แล้วระบุว่าใครกินเมนูใดบ้าง ก่อนคำนวณยอดที่แต่ละคนต้องจ่าย

## ฟีเจอร์

- อัปโหลดรูปหรือถ่ายรูปใบเสร็จจากกล้อง
- Google Gemini อ่านชื่อร้าน เมนู จำนวน ราคาต่อหน่วย Service charge, VAT, ส่วนลด และยอดรวม
- ตรวจและแก้ข้อมูลด้วยมือก่อนคำนวณ
- เมนูเดียวกันที่สั่งหลายชิ้นถูกแยกเป็น `#1`, `#2`, ... เพื่อให้ระบุคนกินแต่ละครั้งต่างกันได้
- เมนูหนึ่งแชร์กันหลายคนได้
- Service/VAT/ส่วนลด กระจายตามสัดส่วนค่าอาหารของแต่ละคน
- ปัดเศษระดับสตางค์โดยรักษายอดรวม
- ดาวน์โหลดผลลัพธ์เป็น JSON
- มีโหมดกรอกเองแม้ไม่ใช้ Gemini API

## 1. สร้าง Google Gemini API key

สร้าง API key ใน Google AI Studio แล้วเก็บ key ไว้เป็นความลับ ห้าม commit ลง GitHub

โปรแกรมรองรับตัวแปร `GEMINI_API_KEY` และ `GOOGLE_API_KEY` โดยแนะนำให้ใช้ `GEMINI_API_KEY`

## 2. ติดตั้ง

ต้องมี Python 3.10+ แนะนำ Python 3.11 หรือ 3.12

### Windows PowerShell

```powershell
cd receipt-splitter
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python -m streamlit run app.py
```

แก้ `.env` เป็น:

```env
GEMINI_API_KEY=ใส่_api_key_ของคุณตรงนี้
GEMINI_MODEL=gemini-2.5-flash
```

### macOS / Linux

```bash
cd receipt-splitter
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

แก้ `.env` แล้วรัน:

```bash
python -m streamlit run app.py
```

จากนั้นเปิด URL ที่ Streamlit แสดง โดยทั่วไปคือ `http://localhost:8501`

## ตั้ง key ผ่าน Environment Variable แทน .env

Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="YOUR_GOOGLE_API_KEY"
python -m streamlit run app.py
```

macOS / Linux:

```bash
export GEMINI_API_KEY="YOUR_GOOGLE_API_KEY"
python -m streamlit run app.py
```

## เปลี่ยนโมเดล

ค่าเริ่มต้นคือ `gemini-2.5-flash` และเปลี่ยนได้ด้วย `GEMINI_MODEL` เช่น:

```env
GEMINI_MODEL=gemini-2.5-flash
```

เลือกโมเดลที่รองรับ image input และเปิดให้ใช้กับบัญชี Google AI Studio ของคุณ

## ตัวอย่างกรณีเมนูซ้ำ

ใบเสร็จ: `กะเพรา x2` ราคาชิ้นละ 100 บาท

หลังยืนยันรายการ แอปจะแสดง:

- กะเพรา #1 — เลือก A, B → คนละ 50 บาท
- กะเพรา #2 — เลือก C → 100 บาท

## ทดสอบ

```bash
pytest -q
```

## ความปลอดภัย

- `.env` ถูกใส่ไว้ใน `.gitignore` แล้ว
- อย่านำ API key ไปเขียนตรง ๆ ใน `app.py`
- หากเคยเผยแพร่ key ใน GitHub/แชต ให้ revoke key แล้วสร้างใหม่

## หมายเหตุ

ผลจาก AI ควรตรวจทานกับใบเสร็จก่อนกดคำนวณเสมอ โดยเฉพาะใบเสร็จที่ภาพเบลอ มีส่วนลดซับซ้อน หรือร้านแสดง VAT/Service ในรูปแบบไม่มาตรฐาน
