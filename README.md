# 💑 บัญชีค่าใช้จ่าย ปะป๊า & หม่ามี้

## การติดตั้งและใช้งาน

### ขั้นตอนที่ 1 — ติดตั้ง Python packages
```bash
pip install -r requirements.txt
```

### ขั้นตอนที่ 2 — สร้าง Google Service Account (ทำครั้งเดียว)

1. ไปที่ [Google Cloud Console](https://console.cloud.google.com/)
2. สร้าง Project ใหม่ หรือเลือก Project เดิม
3. เปิดใช้งาน **Google Sheets API** และ **Google Drive API**
4. ไปที่ **IAM & Admin → Service Accounts → Create Service Account**
5. ตั้งชื่อ เช่น `expense-tracker`
6. คลิก **Keys → Add Key → Create new key → JSON**
7. บันทึกไฟล์ที่ได้ชื่อว่า `credentials.json` ไว้ในโฟลเดอร์เดียวกับ `app.py`

### ขั้นตอนที่ 3 — แชร์ Google Sheets ให้ Service Account
1. เปิด `credentials.json` หาค่า `client_email` (จะมีรูปแบบ `xxxx@xxxx.iam.gserviceaccount.com`)
2. เปิด Google Sheets → คลิก **Share**
3. เพิ่ม email ของ Service Account → ให้สิทธิ์ **Editor**

### ขั้นตอนที่ 4 — รันโปรแกรม
```bash
streamlit run app.py
```

เปิด browser ที่ `http://localhost:8501`

---

## ฟีเจอร์
- ✅ บันทึกค่าใช้จ่าย sync กับ Google Sheets อัตโนมัติ
- ✅ หมวดหมู่ค่าใช้จ่าย
- ✅ คำนวณหาร 2 / ระบุว่าใครจ่าย / ไม่คิด
- ✅ Dashboard กราฟวงกลม, กราฟแท่ง, กราฟเส้นรายวัน
- ✅ สรุปส่วนต่างว่าใครต้องคืนเงินใคร
- ✅ Export Excel
- ✅ Filter ตามเดือน / หมวดหมู่ / ค้นหา
