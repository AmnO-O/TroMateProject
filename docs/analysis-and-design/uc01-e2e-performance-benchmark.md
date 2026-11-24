# TroMate — Báo cáo Đo hiệu năng End-to-End & Bóc tách Thành phần (`SCRUM-123`)

Tài liệu tổng hợp số đo hiệu năng thực tế ở trạng thái hiện tại trên nhánh `feat/scrum-123/pa4-uc01-expense-log` (kiến trúc Single `UnitOfWork`, kiểm tra member trên RAM, và `SELECT 1` warm-up lúc khởi động server).

---

## 1. Môi trường & Điều kiện đo

| Thông số | Giá trị thực tế |
| :--- | :--- |
| **Runtime & Framework** | Python 3.12.16, FastAPI, `aiogram` 3.31.0, SQLAlchemy 2.0 (async) + `asyncpg` |
| **Database** | Managed PostgreSQL 18.7 trên Neon (`ap-southeast-1`, Singapore `-pooler`) |
| **LLM Extractor** | Google Gemini API (`gemini-3.5-flash-lite`, fallback sang `vnd_parser.py`) |
| **Phạm vi đo** | `time.perf_counter()` từ `Update` vào `AiogramEngine` tới khi dựng xong HTML Card (`Message.answer` mock để tránh spam group thật) |
| **Tham chiếu mạng Telegram** | Đo riêng HTTP RTT thực tế tới `https://api.telegram.org/bot.../getMe` (`804.86 ms`, HTTP 200) |

---

## 2. Benchmark đơn lẻ từng Module

### 2.1. `AIExtractionAdapter` (Subtask 1 — 4 câu mẫu tiếng Việt)

| Câu đầu vào | Fallback `vnd_parser.py` (ms) | Gemini `gemini-3.5-flash-lite` (ms) | Nguồn trả về |
| :--- | ---: | ---: | :--- |
| `Đi chợ mua thịt cá hết 150k chia tao với Nam` | `0.078` | `977.10` | `gemini` |
| `Tiền điện tháng 10 650k chia đều cả phòng` | `0.105` | `805.31` | `gemini` |
| `Trà sữa 120k tao trả, Minh 70k, An 50k` | `0.050` | `1,114.70` | `gemini` |
| `Đóng tiền wifi 1 củ rưỡi` | `0.060` | `822.11` | `gemini` |
| **Trung bình 4 câu** | **`0.073 ms`** | **`929.81 ms`** | Fallback nhanh hơn `12,667.7x` |

### 2.2. `ExpenseParser` (Subtask 2 — feed thẳng `RawExtractionResult`)

| Kịch bản đo | Thời gian | Ghi chú |
| :--- | ---: | :--- |
| **Batch 3 payload mẫu** (EQUAL + CUSTOM_AMOUNT) | `0.1331 ms` | Chuẩn hóa VND slang + quy tắc phần dư `§2.5.3` |
| **1,000 lượt liên tiếp** | `14.44 ms` | Trung bình **`14.44 µs/lượt`** |

---

## 3. Bóc tách End-to-End lệnh `/new` trên Neon PostgreSQL

| Thành phần trong luồng `/new` -> Card | Run 1: Fallback (`Groceries`, BR03, `85,000đ`) | Run 2: Gemini (`Utilities`, BR02, `650,000đ`) | Run 3: Fallback (`Food & Drinks`, BR03, `45,000đ`) |
| :--- | ---: | ---: | ---: |
| **Startup Warmup (`SELECT 1`)** | `1,278.738 ms` *(chạy 1 lần lúc boot)* | *(đã warm)* | *(đã warm)* |
| **1. `AIExtractionAdapter.extract`** | `0.254 ms` | `1,337.074 ms` | `0.066 ms` |
| **2. `Room + Member` Check (1 UoW / RAM)** | `526.184 ms` | `428.931 ms` | `515.459 ms` |
| **3. `ExpenseParser.parse` (CPU)** | `0.192 ms` | `0.090 ms` | `0.041 ms` |
| **4. `Category + Expense` Write (1 UoW)** | `477.297 ms` | `587.150 ms` | `471.716 ms` |
| **5. Card HTML + Inline Keyboard** | `0.142 ms` | `0.104 ms` | `0.161 ms` |
| **6. `Aiogram` Router Overhead** | `0.469 ms` | `0.357 ms` | `0.401 ms` |
| **Tổng DB Neon (2 + 4)** | **`1,003.481 ms`** | **`1,016.081 ms`** | **`987.176 ms`** |
| **TỔNG E2E (`/new` -> sẵn sàng gửi Card)** | **`1,004.537 ms`** | **`2,353.706 ms`** | **`987.845 ms`** |
| *Verify `SELECT` đọc lại từ Neon* | `657.506 ms` | `686.112 ms` | `986.295 ms` |

---

## 4. Thời gian chạy các lệnh Bot nhẹ (`/start`, `/help`, `/app`, `/balance`)

Đo trung bình 10 lượt trên `AiogramEngine` (với `bot._me` đã cache):

| Lệnh | Text Builder (CPU) | Router + Keyboard | Tổng xử lý Backend (avg) | Lần chạy đầu (`1st`) | Ước tính gồm gửi Telegram API (`+804.86 ms`) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `/start` (private) | `0.15 µs` | `0.1181 ms` | **`0.1183 ms`** | `0.3454 ms` | `~804.98 ms` |
| `/start` (group) | `0.34 µs` | `0.2513 ms` | **`0.2517 ms`** | `0.1087 ms` | `~805.11 ms` |
| `/help` | `0.24 µs` | `0.1195 ms` | **`0.1197 ms`** | `0.1298 ms` | `~804.98 ms` |
| `/help@tromate_bot` | `0.24 µs` | `0.1382 ms` | **`0.1385 ms`** | `0.1441 ms` | `~805.00 ms` |
| `/app` (group) | `0.00 µs` | `0.2100 ms` | **`0.2100 ms`** | `0.1890 ms` | `~805.07 ms` |
| `/balance` (mock) | `4.12 µs` | `0.3187 ms` | **`0.3228 ms`** | `0.2614 ms` | `~805.18 ms` |

---

## 5. Tổng hợp Phân bổ Độ trễ End-to-End thực tế (bao gồm gửi tin nhắn ra Telegram)

| Luồng thực thi | Xử lý CPU nội bộ | Gemini API | Neon DB (1 UoW) | Telegram API RTT (`sendMessage`*) | Tổng thời gian user cảm nhận |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Lệnh nhẹ (`/help`, `/start`, `/app`, `/balance`)** | `~0.12 – 0.32 ms` | `0 ms` | `0 ms` | `~804.86 ms` | **`~0.81 giây`** |
| **`/new` (Fallback `vnd_parser`)** | `~0.7 – 0.9 ms` | `0 ms` | `~987 – 1,003 ms` | `~804.86 ms` | **`~1.79 – 1.81 giây`** |
| **`/new` (Gemini `3.5-flash-lite`)** | `~0.6 – 0.9 ms` | `~930 – 1,337 ms` | `~1,016 ms` | `~804.86 ms` | **`~2.75 – 3.16 giây`** |

*\*Ghi chú: Telegram API RTT được ước tính dựa trên phép đo thực tế `GET /getMe` (`804.86 ms`, HTTP 200) từ môi trường local tới `api.telegram.org`.*
