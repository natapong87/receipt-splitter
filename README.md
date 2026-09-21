# Receipt Splitter Mobile UI v14

เวอร์ชันนี้แก้ layout ปุ่มลบสมาชิกสำหรับมือถือโดยเปลี่ยนแต่ละแถวเป็น `st.columns(..., wrap=False)` และกำหนดคอลัมน์ปุ่มลบให้มีความกว้างคงที่ จึงไม่เหลื่อมขึ้นลงตามความยาวของชื่อหรือขนาดหน้าจอ

## สิ่งที่แก้ใน v14

- ชื่อสมาชิกและปุ่มลบอยู่กึ่งกลางแนวตั้งในแถวเดียวกัน
- ปุ่มลบทุกปุ่มเรียงเป็นแนวเดียวกันด้านขวา
- ปุ่มลบขนาด `30 x 30 px` พร้อมพื้นที่คอลัมน์คงที่ `38 px`
- ชื่อที่ยาวจะตัดด้วย `…` แทนการดันหรือทับปุ่ม
- แถวสมาชิกไม่เกิด internal scrolling และไม่ stack บนมือถือ
- การลบสมาชิกใช้ callback และนำสมาชิกออกจากทุกรายการให้อัตโนมัติ

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run app.py
```

## Streamlit Community Cloud

อัปโหลดไฟล์ทั้งหมด ยกเว้น `.env` และตั้งค่า Secrets:

```toml
GEMINI_API_KEY = "your_key_here"
GEMINI_MODEL = "gemini-3.8-flash"
```
