# Giai đoạn 2: Dữ liệu lịch sử Dukascopy

Ngày: 2026-11-05 · Ưu tiên: cao · Phụ thuộc: giai đoạn 1 · Trạng thái: hoàn thành 2026-11-08 · Review: tự rà soát 2026-11-06

Tổng quan: [plan.md](plan.md) · Trước: [giai đoạn 1](phase-01-project-foundation.md)

## Mục tiêu
Có dữ liệu M1 **bid và ask** sạch cho EURUSD, GBPUSD, XAUUSD từ 2020-01 đến 2026-10, lưu Parquet. Có bộ resample sang M5/M15/H1 và báo cáo chất lượng dữ liệu.

## Bối cảnh
- `dukascopy-node` là CLI Node 18+, máy đã có Node 24, chạy bằng `npx`. Timestamp của Dukascopy là UTC.
- Cờ CLI dự kiến: `-i <instrument> -from YYYY-MM-DD -to YYYY-MM-DD -t m1 -p bid|ask -f csv`. **Kiểm tra lại** bằng `npx dukascopy-node --help` và danh sách instrument (mã chính xác của vàng) trước khi viết code.
- Tải cả bid lẫn ask để có **spread thật theo từng phút**. Đây là thứ quyết định kết quả backtest với SL hẹp.

## File (đề xuất)
| Đường dẫn | Hành động | Lý do |
|---|---|---|
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/data/dukascopy.py` | tạo | Gọi CLI qua `subprocess` (danh sách tham số, không qua shell), tải theo tháng, tải tiếp được khi bị gián đoạn |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/data/store.py` | tạo | Ghi/đọc Parquet `data/m1/{symbol}/{yyyy}-{mm}.parquet` (cột: `ts, bid_o..c, ask_o..c, volume`) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/data/resample.py` | tạo | M1 → M5/M15/H1. Mỗi nến có `ts` (giờ mở) và `closed_at` |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/data/quality.py` | tạo | Kiểm tra và xuất báo cáo chất lượng |
| `/Users/nhhai7/LocalData/TVTools/tests/data/` | tạo | Test resample và quality trên dữ liệu mẫu nhỏ |
| `/Users/nhhai7/LocalData/TVTools/tests/fixtures/` | tạo | Vài ngày M1 thật (nhỏ, commit được) làm dữ liệu test cố định |

## Thiết kế
- **Quy ước giá:** phát hiện ICT dùng **bid** (giống chart MT/TradingView). Khớp lệnh: long mua ở ask và bán ở bid, short ngược lại.
- **Không look-ahead từ đầu:** mỗi nến có `closed_at = ts + timeframe`. Mọi code phía sau chỉ được dùng nến có `closed_at ≤ thời điểm hiện tại`.
- **Resample:** neo theo UTC cho M5/M15/H1 (các mốc này trùng giữa UTC và NY vì lệch giờ là số nguyên giờ). Mức theo ngày (PDH/PDL) **không** resample D1 mà gom nhóm theo `trading_day()` của giai đoạn 1, để tránh lệch giữa UTC và ngày NY.
- **Tải theo tháng:** mỗi tháng một file. Tháng đã có file và đã qua kiểm tra thì bỏ qua (idempotent). Tháng hiện tại luôn tải lại.

## Kiểm tra chất lượng (báo cáo `reports/data-quality-{symbol}.md`)
- Trùng timestamp, timestamp không tăng dần.
- Tính nhất quán OHLC: `low ≤ open, close ≤ high`; `ask ≥ bid`.
- Khoảng trống > 5 phút trong giờ thị trường mở (tuần FX từ Chủ nhật 17:00 đến thứ Sáu 17:00 NY, trừ ngày lễ NYSE trọn ngày qua `market_open()` trong `core/timeutil.py`). Đếm số lượng và liệt kê top.
- Phân phối spread theo giờ NY (trung vị, p95). Phải thấy rõ spread giãn lúc 17:00 NY và lúc ra tin.
- ~~Nến "phẳng" (O=H=L=C, volume 0) ngoài cuối tuần.~~ Bỏ: API Dukascopy chỉ trả phút có tick; `dukascopy-node` chỉ tạo nến flat giả (giá close trước, volume 0) khi bật `-fl`. Không bật `-fl`, nên phút không tick hiện ra dưới dạng khoảng trống và resample dựng nến từ các phút có thật.

## Các bước
1. Chạy `npx dukascopy-node --help`, xác nhận cờ CLI và mã instrument của 3 mã. Ghi kết quả vào docstring.
2. Viết `dukascopy.py` + `store.py`. Tải thử 1 tháng EURUSD bid và ask.
3. Viết `quality.py`. Chạy trên tháng thử.
4. Tải toàn bộ 2020-01 → 2026-10 cho 3 mã. Chạy nền, tốn thời gian.
5. Viết `resample.py` + test: tổng hợp 5 nến M1 bằng tay phải khớp M5. `closed_at` đúng.
6. Lệnh CLI: `tvtools data fetch --symbol EURUSD --from 2020-01 --to 2026-10`, `tvtools data check --symbol EURUSD`.

## Việc cần làm
- [x] Xác nhận cờ CLI và mã instrument
- [x] Tải + lưu Parquet theo tháng, tải tiếp được
- [x] Báo cáo chất lượng (người dùng duyệt 2026-11-08)
- [x] Tải đủ 3 mã, 2020-01 → 2026-10
- [x] Resample + test
- [x] Dữ liệu test cố định (`tests/fixtures/eurusd_m1_2024-01-09_10.csv`, test trong `tests/data/test_real_fixture.py`)

### Tiến độ (cập nhật 2026-11-06, tạm dừng)

#### Đã làm
- **Code:** downloader theo tháng (`data/dukascopy.py`), lưu Parquet atomic và có kiểm tra (`data/store.py`), báo cáo chất lượng (`data/quality.py`), resample M5/M15/H1 (`data/resample.py`), CLI `tvtools data fetch|check`. Thêm `market_holidays()` và `market_open()` vào `core/timeutil.py`.
- **Đã xác nhận với `dukascopy-node` 1.51.1:** cờ CLI đúng như dự kiến; mã instrument là `eurusd`, `gbpusd`, `xauusd`. Dữ liệu M1 của cả 3 mã có từ 2003.
- **Quyết định thiết kế:**
  - Không dùng `-fl`. API chỉ trả phút có tick; bật `-fl` thì thư viện tự sinh nến giả (giá = close trước, volume 0). Vì vậy đã bỏ phép kiểm "nến phẳng" khỏi báo cáo.
  - Resample giữ mọi cửa sổ có ít nhất 1 nến M1. Chống look-ahead nhờ `closed_at`, không nhờ việc đếm đủ phút.
  - Khoảng trống chỉ tính trong tuần FX (Chủ nhật 17:00 đến thứ Sáu 17:00 NY), trừ ngày lễ NYSE trọn ngày. Ngày lễ đóng ngày FX kết thúc lúc 17:00 NY của ngày đó.
- **Truy cập Dukascopy:** lỗi `fetch failed` trước đây **không phải do WAF**. Mạng nội bộ giải mã HTTPS bằng CA riêng (`CN=MWG`); macOS tin CA này nhưng Node thì không (`UNABLE_TO_VERIFY_LEAF_SIGNATURE`). `node_env()` cho `npx` chạy với `NODE_OPTIONS=--use-system-ca`. Không gặp thử thách WAF (không sinh file token).
- **Đã kiểm trên dữ liệu thật EURUSD 2024-01:**
  - 31688 dòng; chạy `fetch` lần hai ra `downloaded 0, skipped 1`.
  - `data check`: 0 trùng, 0 lỗi OHLC, 0 ask < bid, 0 khoảng trống > 5 phút.
  - Spread trung vị 07–11h NY là **0.3 pip**, đạt tiêu chí. Lúc 17:00 NY spread giãn ra 1.7 pip (p95 4.1).
  - Bid/ask không lệch timestamp. Dữ liệu bắt đầu 2024-01-01 17:00 NY, khớp lịch nghỉ New Year.
- **Kiểm tra:** `uv run pytest` 54 passed (coverage 93% với `--cov=tvtools`), `ruff check` passed, `mypy src` passed, `uv build --system-certs` passed.

#### Cập nhật 2026-11-08 (máy mới `/Users/hainguyen/LocalData/T-tools`)
- Đã tải xong EURUSD, GBPUSD, XAUUSD: 82/82 file mỗi mã (`data/m1/`, 220 MB). Đã chạy `data check` cho cả 3 mã.
- Kết quả báo cáo: cả 3 mã đều có 0 trùng, 0 lỗi OHLC, 0 ask < bid.
- Spread trung vị 07–11h NY: EURUSD 0.3 pip, GBPUSD 0.8 pip, XAUUSD 37–39 "pip" với pip = 0.01, tức khoảng 0.38 USD.
- **EURUSD 2024-12:** Dukascopy không có ask cho trọn 3 ngày giao dịch NY 02/12, 05/12, 06/12 (4188 phút chỉ có bid). Người dùng chọn **bỏ phút một phía**:
  - Khi bid và ask lệch nhau, code tải lại tháng đó một lần. Nếu hai lần ra cùng tập phút thì bỏ phút một phía, ghi số phút vào `attrs.one_sided_minutes` của file Parquet, và báo cáo in dòng "One-sided source minutes dropped". Nếu hai lần khác nhau thì báo lỗi "unstable download".
- **Bỏ cache `-ch`.** Bắt buộc dùng `-v`: thiếu `-v` thì `dukascopy-node` sinh nến phẳng cho phút không có tick, ví dụ Chủ nhật trước giờ mở cửa.
- Khoảng trống: EURUSD và GBPUSD có lỗ chung ở nguồn (2024-10-09 23:04 UTC dài 66 phút; 2025-03-03 10:31 UTC dài 25 phút). XAUUSD có 1725 khoảng trống, chủ yếu là giờ nghỉ hằng ngày 17:00–18:00 NY của kim loại và các ngày đóng sớm (Thanksgiving, Giáng sinh). Bộ đếm khoảng trống hiện chỉ tính theo lịch FX, chưa trừ các giờ nghỉ này.
- Máy này không cần sửa `~/.npm`. `uv build` chạy được không cần `--system-certs`.

#### Đang làm (dừng giữa chừng, ghi ngày 2026-11-06, đã xử lý xong ở cập nhật trên)
- Tải nền 3 mã từ 2020-01 đến 2026-10. Người dùng đã dừng tác vụ khi đang ở EURUSD.
- Hiện có trong `data/m1/` (đều đã kiểm tra hợp lệ):
  - EURUSD: 15/82 file (2020-01 → 2021-02 và 2024-01).
  - GBPUSD: 0/82. XAUUSD: 0/82.
- Tốc độ khoảng 8 giây một tháng, nên phần còn lại (khoảng 231 tháng) mất chừng 30–40 phút nếu không bị giới hạn tốc độ.
- Chạy tiếp từ chỗ dừng (tháng đã có tự được bỏ qua):
  ```sh
  # Bỏ dòng export nếu đã sửa quyền ~/.npm (xem "Lưu ý máy này").
  export npm_config_cache="$PWD/.npm-cache"
  for s in EURUSD GBPUSD XAUUSD; do
    uv run python -m tvtools data fetch --symbol $s --from 2020-01 --to 2026-10
  done
  ```
  Nếu một tháng lỗi thì lệnh dừng; chạy lại cùng lệnh là tiếp tục được.

#### Cần làm
1. ~~Tải xong 3 mã cho đủ 82 file mỗi mã.~~ Xong 2026-11-08.
2. Chạy `tvtools data check --symbol {EURUSD,GBPUSD,XAUUSD}`. Người dùng xem danh sách khoảng trống trong `reports/data-quality-*.md`, rồi tick "Báo cáo chất lượng".
3. ~~Kiểm tra spread XAUUSD trên dữ liệu thật để xác nhận quy ước pip = 0.01 hợp lý.~~ Đã đổi pip XAUUSD sang 0.1 USD (2026-11-08); spread trung vị khoảng 3.8 pip.
4. ~~Nếu có tháng báo "bid/ask timestamps disagree": hiện code dừng hẳn (fail-fast). Khi đó cần quyết định cách xử lý: bỏ phút một phía hay điền giá phía còn lại.~~ Đã quyết: bỏ phút một phía.
5. ~~Cắt vài ngày M1 thật (ví dụ một ngày thường và ngày quanh 17:00 NY, từ EURUSD 2024-01) làm fixture trong `tests/fixtures/`, thay CSV tự tạo. Rồi tick "Dữ liệu test cố định".~~ Xong 2026-11-08: 2 ngày giao dịch EURUSD 2024-01-09/10 (17:00 NY → 17:00 NY, 2872 phút). File `m1_sample.csv` tự tạo vẫn giữ cho test resample tính tay.
6. ~~Khi đủ tiêu chí chấp nhận: đổi trạng thái giai đoạn sang hoàn thành, cập nhật `plan.md`.~~ Xong 2026-11-08 (pytest 62 passed, ruff, mypy, uv build passed).

#### Lưu ý máy này
- `~/.npm` có 1457 file thuộc root, làm `npx` lỗi `EACCES`. Sửa một lần bằng `sudo chown -R $(id -u):$(id -g) ~/.npm`; trước đó thì đặt `npm_config_cache` sang thư mục khác.
- `uv build` cần `--system-certs`, cùng nguyên nhân CA nội bộ.
- Thay đổi chưa commit.

## Tiêu chí chấp nhận
- Mỗi mã có đủ 82 file tháng. Báo cáo chất lượng không có lỗi trùng hoặc lỗi OHLC. Khoảng trống được liệt kê và chấp nhận được (bạn xem báo cáo).
- Spread trung vị EURUSD trong 07:00–11:00 NY nằm trong khoảng hợp lý (khoảng 0.1–0.5 pip với dữ liệu Dukascopy). Nếu lệch xa thì xem lại quy ước pip.
- `uv run pytest tests/data` qua. Chạy `fetch` lần hai không tải lại tháng đã có.

## Rủi ro
- Dukascopy chặn hoặc giới hạn tốc độ khi tải nhiều: tải theo tháng, có retry với backoff, chạy nền.
- Spread Dukascopy (ECN) **hẹp hơn** broker CFD. Giai đoạn 6 phải cộng thêm spread và phí hoa hồng của broker (tham số `extra_spread_pips`, `commission_per_lot`) thay vì chỉ dùng spread Dukascopy.
- Dung lượng: khoảng 2–3 triệu nến/mã cho bid+ask. Parquet nén vài chục MB/mã. Không đáng lo.
