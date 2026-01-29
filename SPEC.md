คุณคือวิศวกร backend ระดับอาวุโส

ฉันต้องการให้คุณออกแบบและพัฒนาโปรเจค FastAPI
ซึ่งทำหน้าที่เป็น “worker” สำหรับประมวลผลไฟล์ PDF

บริบทของระบบ:
- ระบบนี้มี Next.js เป็นฝั่ง UI และ API สำหรับผู้ใช้งาน
- FastAPI ทำงานอยู่ใน Docker container แยกต่างหาก
- ทั้ง Next.js และ FastAPI ใช้ Docker volume ร่วมกันที่ path `/shared`
- FastAPI ไม่ต้องมี UI และไม่ต้องจัดการ authentication ใด ๆ
- FastAPI ทำงานภายใน network ภายในเท่านั้น

โครงสร้างโฟลเดอร์ที่ใช้ร่วมกัน (ภายใน container):
/shared
 ├─ inbox/        # เก็บไฟล์ PDF ที่ Next.js อัพโหลดเข้ามา
 ├─ processing/   # โฟลเดอร์ทำงานชั่วคราว (ถ้าจำเป็น)
 ├─ output/       # เก็บไฟล์ผลลัพธ์หลังประมวลผล
 └─ logs/         # log การทำงาน (ห้ามเก็บข้อมูลส่วนบุคคลแบบเต็ม)

หน้าที่ของ FastAPI worker:
1. รับคำสั่งประมวลผลโดยอ้างอิง `jobId` (string)
2. อ่านไฟล์จาก `/shared/inbox/{jobId}.pdf`
3. ประมวลผล PDF ทีละหน้า โดย:
   - ดึงข้อความจากแต่ละหน้า
   - ตรวจหาเลขประจำตัวประชาชนไทย (13 หลัก) ด้วย regex
   - ถ้าไม่พบ ให้กำหนดค่าเป็น `unknown`
   - แยก PDF ทีละหน้าออกเป็นไฟล์ใหม่
4. บันทึกไฟล์ผลลัพธ์ที่:
   `/shared/output/{jobId}/{citizenId}.pdf`
5. ส่งผลลัพธ์กลับเป็น JSON โดยประกอบด้วย:
   - jobId
   - จำนวนหน้าที่ประมวลผล
   - รายชื่อไฟล์ที่สร้าง
   - สถานะการทำงาน (success / partial / failed)
6. จัดการ error และ log อย่างเหมาะสม โดยไม่เปิดเผยข้อมูลส่วนบุคคล

ข้อกำหนดด้านเทคนิค:
- ใช้ FastAPI
- ใช้ไลบรารี pypdf หรือ pdfplumber
- OCR เป็น optional (ไม่ต้องบังคับใช้ในเวอร์ชันแรก)
- ตัว service ต้องเป็น stateless (ยกเว้น filesystem)
- ต้องตรวจสอบและสร้างโฟลเดอร์ใน `/shared` อัตโนมัติเมื่อ service เริ่มทำงาน
- โค้ดต้องอ่านง่าย แยก responsibility ชัดเจน และพร้อมใช้งานจริง

สิ่งที่ต้องการให้ส่งมอบ:
- โครงสร้างโปรเจค FastAPI
- ไฟล์ main.py
- logic สำหรับประมวลผล PDF
- Dockerfile
- requirements.txt
- ตัวอย่าง API endpoint:
  - POST /process/{jobId}
  - GET /status/{jobId} (ตรวจสอบสถานะจาก filesystem)

ไม่ต้องใช้ database
ไม่ต้องเชื่อมต่อ cloud service
ไม่ต้องมี authentication

หากมีการตัดสินใจด้านสถาปัตยกรรม ให้ช่วยอธิบายเหตุผลสั้น ๆ ประกอบ