# Giai đoạn 4: Chart kiểm tra bằng mắt

Ngày: 2026-11-05 · Ưu tiên: cao · Phụ thuộc: giai đoạn 3 · Trạng thái: chưa bắt đầu · Review: chưa

Tổng quan: [plan.md](plan.md) · Trước: [giai đoạn 3](phase-03-ict-detectors.md) · Sau: [giai đoạn 5](phase-05-model-and-risk.md)

## Mục tiêu
Cho phép bạn xem những gì máy phát hiện trên chart nến, theo từng ngày giao dịch. Chỉnh định nghĩa cho đến khi khớp với mắt bạn, rồi **khóa tham số detector**. Đây là **điểm kiểm soát bắt buộc**.

## File (đề xuất)
| Đường dẫn | Hành động | Lý do |
|---|---|---|
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/viz/chart.py` | tạo | Plotly candlestick, ghi ra 1 file HTML tự chứa cho mỗi ngày |
| `/Users/nhhai7/LocalData/TVTools/tests/viz/test_chart.py` | tạo | Smoke test: tạo được HTML có đủ các lớp vẽ |
| `/Users/nhhai7/LocalData/TVTools/reports/review/` | sinh ra | Thư mục chứa HTML, đã gitignore |

## Nội dung chart (mỗi ngày, M5, giờ hiển thị là giờ VN và giờ NY)
- Nền màu cho phiên Á, London KZ, NY AM KZ. Vạch dọc tại 12:00 NY (giờ đóng hết lệnh).
- Đường ngang: Asia H/L, London H/L, PDH/PDL, equal H/L. Mỗi đường kết thúc ở điểm bị sweep.
- Đánh dấu: swing (tam giác), sweep (✕), nến displacement (viền đậm), MSS (mũi tên tại nến phá), FVG (hình chữ nhật tới khi bị lấp hoặc hết ngày).
- Từ giai đoạn 5 trở đi: thêm tín hiệu và lệnh (vào lệnh, SL, TP, thoát), dùng chung module này.
- Tooltip của mỗi đối tượng hiện `formed_at` và `confirmed_at`, để bạn thấy máy biết sự kiện **khi nào**.

## Lệnh CLI
- `tvtools review --symbol EURUSD --date 2025-03-12`: xuất một ngày.
- `tvtools review --symbol EURUSD --sample 20 --seed 1`: xuất 20 ngày ngẫu nhiên kèm `index.html` liệt kê các ngày.

## Quy trình kiểm tra cùng bạn
1. Xuất 20 ngày ngẫu nhiên cho mỗi mã EURUSD và GBPUSD, trong dữ liệu **IS** (2020–2023). Không xem OOS.
2. Với mỗi ngày, bạn ghi lại: thấy gì mà máy bỏ sót, máy thấy gì sai. Ghi vào `plans/20261105-1739-ict-intraday-system/reports/visual-review-notes.md`.
3. Chỉnh tham số hoặc định nghĩa ở giai đoạn 3, chạy lại test. Lặp lại tối đa 3 vòng.
4. Khi bạn đồng ý: ghi bộ tham số detector cuối cùng vào `config/default.toml` với ghi chú "locked". Ghi ngày khóa vào file ghi chú.

## Việc cần làm
- [ ] `chart.py` với đủ các lớp vẽ
- [ ] Lệnh `review` (một ngày và mẫu ngẫu nhiên)
- [ ] Vòng xem 1, sửa
- [ ] Vòng xem 2 (và 3 nếu cần)
- [ ] Khóa tham số detector

## Tiêu chí chấp nhận
- `uv run pytest tests/viz` qua. HTML mở được trong trình duyệt, không cần mạng (plotly nhúng sẵn).
- Bạn xác nhận bằng chữ: trong ≥ 80% số ngày xem, swing, sweep, MSS và FVG máy vẽ khớp với cách bạn đọc chart.
- Tham số detector đã được khóa trong config.

## Rủi ro
- Chỉnh quá nhiều theo vài ngày cụ thể. Chỉ chỉnh định nghĩa khi lỗi lặp lại ở ≥ 3 ngày.
- Xem dữ liệu OOS sẽ làm hỏng tính khách quan. Lệnh `review` mặc định **từ chối** ngày thuộc OOS (≥ 2024-01-01), trừ khi có cờ `--allow-oos` (chỉ dùng ở giai đoạn 6 trở đi).
