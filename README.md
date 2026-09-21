# Receipt Splitter — Gemini / Mobile Deploy Edition

เว็บแอป Streamlit สำหรับอ่านใบเสร็จร้านอาหารด้วย Google Gemini แล้วระบุว่าใครกินเมนูใดบ้าง ก่อนคำนวณยอดที่แต่ละคนต้องจ่าย

## จุดเด่นของเวอร์ชันนี้

- ใช้ Google Gemini **Interactions API**
- ค่าเริ่มต้น `gemini-3.8-flash`
- ถ้าโมเดลที่ตั้งไว้ตอบ 404 แอปจะลอง fallback model ให้อัตโนมัติ
- ใช้ได้ทั้ง local `.env` และ Streamlit Community Cloud `Secrets`
- อัปโหลดรูปหรือถ่ายรูปใบเสร็จจากมือถือ
- แยกเมนู `x2`, `x3` เป็น #1, #2, #3 เพื่อระบุคนกินต่างกันได้
- เมนูหนึ่งแชร์กันหลายคนได้
- Service / VAT / ส่วนลด กระจายตามสัดส่วนค่าอาหาร
- ตรวจยอดรวมกับยอดบนใบเสร็จ
- มีโหมดกรอกเอง แม้ไม่ใช้ AI

## รันบนคอม

ต้องมี Python 3.10+ (แนะนำ 3.11 หรือ 3.12)

### Windows PowerShell

```powershell
cd receipt-splitter
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python -m streamlit run app.py
```

ใน `.env` ใส่:

```env
GEMINI_API_KEY=ใส่_google_ai_studio_api_key_ตรงนี้
GEMINI_MODEL=gemini-3.8-flash
```

จากนั้นเปิด URL ที่ Streamlit แสดง โดยทั่วไปคือ `http://localhost:8501`

## Deploy ให้คนอื่นใช้บนมือถือด้วย Streamlit Community Cloud

1. สร้าง GitHub repository แล้ว push ไฟล์ในโฟลเดอร์นี้ขึ้นไป
2. **ห้าม upload `.env`** — โปรเจกต์นี้ใส่ `.env` ใน `.gitignore` แล้ว
3. เข้า Streamlit Community Cloud และเลือก repository
4. Main file path: `app.py`
5. ใน **Advanced settings / Secrets** ใส่:

```toml
GEMINI_API_KEY = "ใส่_key_ของคุณ"
GEMINI_MODEL = "gemini-3.8-flash"
```

6. Deploy แล้วส่ง URL `https://...streamlit.app` ให้เพื่อนได้เลย

> ผู้ใช้ปลายทางไม่ต้องมี Python และไม่ต้องมี Gemini API key ของตัวเอง เพราะ API ถูกเรียกฝั่ง server ด้วย Secret ของผู้ deploy

## ถ้า model ใช้งานไม่ได้

แอปจะลอง fallback model ให้อัตโนมัติเมื่อเจอ 404 / model unavailable หากต้องการกำหนดเอง:

```env
GEMINI_MODEL=gemini-3.8-flash
GEMINI_FALLBACK_MODELS=gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash
```

## ตัวอย่างเมนูซ้ำ

ใบเสร็จ: `กะเพรา x2` ราคาชิ้นละ 100 บาท

- กะเพรา #1 → A, B = คนละ 50 บาท
- กะเพรา #2 → C = 100 บาท

## ทดสอบ

```bash
pytest -q
```

## ความปลอดภัย

- อย่าเขียน API key ลง `app.py`
- อย่า commit `.env` หรือ `.streamlit/secrets.toml`
- ถ้า key เคยถูกเผยแพร่ ให้ revoke แล้วสร้างใหม่
- ใบเสร็จจะถูกส่งไปยัง Gemini API เมื่อผู้ใช้กดอ่านด้วย AI

## แชร์สรุปเป็นรูปภาพ

หลังคำนวณยอดแล้ว แอปจะแสดงส่วน **แชร์สรุปให้เพื่อน** พร้อมปุ่ม **บันทึกภาพสรุป (.png)** ภาพประกอบด้วยชื่อร้าน ยอดที่แต่ละคนต้องจ่าย ยอดรวม และรายการที่ถูกแบ่งแล้ว เหมาะสำหรับบันทึกจากมือถือแล้วส่งต่อผ่าน LINE, Messenger หรือแอปแชตอื่น

ฟีเจอร์นี้สร้างภาพบนเซิร์ฟเวอร์จากข้อมูลบิล จึงไม่ต้องอนุญาตสิทธิ์จับภาพหน้าจอของเครื่อง และไม่บันทึกภาพใบเสร็จต้นฉบับลงในภาพสรุป
