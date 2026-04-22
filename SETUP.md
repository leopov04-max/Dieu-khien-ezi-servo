# Hướng dẫn cài đặt & chạy project trên máy mới

## Tổng quan hệ thống

| Thành phần | Vai trò |
|---|---|
| **Arduino Nano** | Điều khiển động cơ EZI-Servo (Step/Dir) |
| **STM32 BluePill** | Đọc cảm biến ADC (PA0, PA1) qua USB Serial |
| **PC (Python)** | Giao diện giám sát + điều khiển cả 2 mạch cùng lúc |

---

## Bước 1 — Cài Python 3.11

> Yêu cầu: Windows 10/11, có kết nối Internet.

### Cách A: Dùng winget (khuyến nghị, không cần tải file)

Mở **PowerShell** hoặc **Command Prompt**, chạy:

```powershell
winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
```

Sau khi cài xong, kiểm tra:

```powershell
py -3.11 --version
```

Kết quả mong đợi: `Python 3.11.x`

### Cách B: Tải thủ công

1. Truy cập: https://www.python.org/downloads/release/python-3119/
2. Tải file: `python-3.11.9-amd64.exe`
3. Chạy installer, **tick vào "Add Python to PATH"** trước khi nhấn Install.

---

## Bước 2 — Cài thư viện Python

Di chuyển vào thư mục project:

```powershell
cd "đường _dẫn_vào_thư_mục"
```

Cài tất cả thư viện từ file `requirements.txt`:

```powershell
py -3.11 -m pip install -r requirements.txt
```

Hoặc cài thủ công từng cái:

```powershell
py -3.11 -m pip install pyserial matplotlib numpy pillow
```

---

## Bước 3 — Xác định COM port

Cắm cả 2 mạch vào máy qua USB, rồi chạy lệnh sau để xem danh sách cổng:

```powershell
py -3.11 -c "import serial.tools.list_ports; [print(p.device, '|', p.description) for p in serial.tools.list_ports.comports()]"
```

Ví dụ kết quả:
```
COM3 | USB-SERIAL CH340 (COM3)       ← Arduino Nano
COM4 | STMicroelectronics STLink ... ← STM32 BluePill
```

---

## Bước 4 — Cấu hình COM port trong code

Mở file `dual_monitor.py`, chỉnh 2 dòng sau (khoảng dòng 43–44):

```python
ARDUINO_PORT = 'COM3'   # ← cổng Arduino Nano  (thay đúng số COM)
STM32_PORT   = 'COM4'   # ← cổng STM32 BluePill (thay đúng số COM)
```

---

## Bước 5 — Nạp code lên vi điều khiển

Dùng **Arduino IDE** nạp từng file:

| File | Nạp vào |
|---|---|
| `ezi_servo.ino` | Arduino Nano |
| `stm32readadc.ino` | STM32 BluePill |

> Lưu ý: Sau khi nạp xong, **đóng Serial Monitor trong Arduino IDE** trước khi chạy Python, nếu không Python sẽ không mở được cổng COM.

---

## Bước 6 — Chạy giao diện

```powershell
py -3.11 dual_monitor.py
```

Hoặc double-click file `run_monitor.bat` (tự động cài thư viện nếu thiếu).

---

## Cấu trúc file project

```
ezi_servo/
├── ezi_servo.ino         Arduino Nano — điều khiển động cơ
├── stm32readadc.ino      STM32 BluePill — đọc ADC cảm biến
├── dual_monitor.py       Python GUI — giám sát & điều khiển
├── run_monitor.bat       Batch file chạy nhanh trên Windows
├── requirements.txt      Danh sách thư viện Python cần thiết
└── SETUP.md              File này
```

---

## Xử lý sự cố thường gặp

| Lỗi | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `serial.SerialException: could not open port` | Sai COM port hoặc Arduino IDE đang giữ cổng | Đóng Arduino IDE Serial Monitor, kiểm tra lại COM port |
| `ModuleNotFoundError: No module named 'serial'` | Chưa cài thư viện | Chạy lại Bước 2 |
| `py -3.11` không nhận | Python chưa cài hoặc chưa vào PATH | Chạy lại Bước 1, chọn "Add to PATH" |
| STM32 không hiện trong danh sách COM | Thiếu driver ST-Link hoặc chưa cắm đúng cổng USB | Cài driver từ trang ST hoặc cắm qua cổng USB native của BluePill |
| Đồ thị không hiện dữ liệu | STM32 đang in chuỗi không phải số | Kiểm tra `stm32readadc.ino` chỉ in 2 số float cách nhau bằng dấu cách |
