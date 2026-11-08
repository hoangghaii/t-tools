# Kế hoạch: Hệ thống tín hiệu ICT trade trong ngày (EURUSD, GBPUSD)

Ngày lập: 2026-11-05 · Chế độ: `--hard` · Gốc dự án: `/Users/nhhai7/LocalData/TVTools`

## Mục tiêu
Xây hệ thống Python phát hiện setup ICT **Sweep → MSS → FVG** trong killzone London và NY AM. Hệ thống backtest có tính phí, chứng minh có/không có lợi thế, rồi gửi tín hiệu Telegram từ dữ liệu cTrader demo, cuối cùng tự đặt lệnh **trên tài khoản demo**.

## Phạm vi
- Có: EURUSD, GBPUSD. XAUUSD chỉ backtest để tính điều kiện mở khóa.
- Có: chỉ trade trong ngày, long và short, đóng hết lệnh lúc 12:00 NY.
- Không: lệnh giữ vài ngày, order block, ML, dashboard web, tài khoản tiền thật, SMT (chỉ ghi lại để làm sau).

## Quyết định chính (từ 3 vòng brainstorm)
| Hạng mục | Quyết định |
|---|---|
| Công nghệ | Python 3.12 (qua `uv`), monolith, pandas, pyarrow, plotly, pytest, ruff, mypy |
| Dữ liệu | Dukascopy M1 bid và ask (spread thật) → Parquet. Thời gian lưu UTC, giờ phiên tính theo `America/New_York` |
| Broker | cTrader Open API (demo Pepperstone/IC Markets), bọc sau `DataSource`/`Broker` |
| Killzone | London 02:00–05:00, NY AM 07:00–11:00 (giờ NY). Silver Bullet là biến thể. Ngừng vào lệnh 11:00, đóng hết 12:00 |
| Rủi ro | Vốn 100 USD, 0.01 lot, SL gồm spread ≤ 20 pip (2%), 1 lệnh mở cùng lúc, dừng sau 2 lệnh thua/ngày, dừng khi –8%/tuần |
| Quản lý lệnh | Không dời SL, không chốt một phần. TP tại liquidity đối diện, ≥ 2R |
| Nguyên tắc lõi | Backtest và chạy thật dùng **cùng một code**. Mỗi sự kiện có `confirmed_at`, không có look-ahead |

## Kiến trúc (đề xuất)
```
src/tvtools/
  core/      types (Bar, Signal, Trade), config, timeutil (UTC↔NY, ngày giao dịch)
  data/      dukascopy, store (Parquet), resample, ctrader (giai đoạn 7)
  ict/       sessions, swings, liquidity, sweep, structure (displacement/MSS), fvg
  models/    sweep_mss_fvg (máy trạng thái)
  risk.py    khối lượng + giới hạn ngày/tuần
  backtest/  engine, fills (mô phỏng trên M1), metrics, report
  viz/       chart HTML kiểm tra bằng mắt
  live/      runner, telegram, broker_ctrader
  cli.py     python -m tvtools <lệnh>
```
Luồng dữ liệu: nến M1 → resample → bộ phát hiện ICT (sự kiện có `confirmed_at`) → máy trạng thái → `Signal` → bộ lọc rủi ro → backtest hoặc chạy thật.

## Các giai đoạn
| # | Giai đoạn | Phụ thuộc | Trạng thái |
|---|---|---|---|
| 1 | [Khung dự án và kiểu dữ liệu lõi](phase-01-project-foundation.md) | — | Hoàn thành 2026-11-06 |
| 2 | [Dữ liệu lịch sử Dukascopy](phase-02-historical-data.md) | 1 | Đang thực hiện, tạm dừng; đã tải được dữ liệu thật, còn tải đủ 3 mã (2026-11-06) |
| 3 | [Bộ phát hiện khái niệm ICT](phase-03-ict-detectors.md) | 2 | Chưa bắt đầu |
| 4 | [Chart kiểm tra bằng mắt](phase-04-visual-review.md) | 3 | Chưa bắt đầu |
| 5 | [Mô hình và bộ lọc rủi ro](phase-05-model-and-risk.md) | 3, 4 | Chưa bắt đầu |
| 6 | [Backtest và quyết định đi tiếp/dừng](phase-06-backtest.md) | 5 | Chưa bắt đầu |
| 7 | [Tín hiệu trực tiếp qua Telegram](phase-07-live-signals.md) | 6 (đạt điều kiện đi tiếp) | Chưa bắt đầu |
| 8 | [Tự đặt lệnh trên demo](phase-08-demo-execution.md) | 7 (chạy thử ổn) | Chưa bắt đầu |

**Điểm kiểm soát bắt buộc (cần bạn duyệt):** cuối giai đoạn 4 (định nghĩa ICT khớp với mắt bạn), cuối giai đoạn 6 (đi tiếp hay dừng), cuối giai đoạn 7 (kết quả chạy thử khớp backtest).

## Giả định
- Dukascopy đủ đại diện cho giá EURUSD/GBPUSD của broker. Sẽ kiểm tra lại ở giai đoạn 7.
- Bạn cài được `uv` (`brew install uv`). Node 24 đã có sẵn cho `dukascopy-node`.
- Máy Mac bật và có mạng trong các phiên khi chạy giai đoạn 7–8.
- Dự án chưa là git repo. Giai đoạn 1 đề xuất `git init` (cần bạn đồng ý).

## Rủi ro lớn nhất
1. Không có lợi thế sau phí. Giai đoạn 6 có thể kết luận "dừng". Đó là kết quả hợp lệ, không phải thất bại của kế hoạch.
2. Overfitting. Giới hạn số biến thể, khóa dữ liệu OOS (out-of-sample), chỉ chạy OOS một lần.
3. Look-ahead bias. Có bài test "prefix invariance" bắt buộc (giai đoạn 3).
4. SDK cTrader ít được cập nhật (0.9.2, Twisted). Phương án dự phòng: WebSocket/JSON (cổng 5036).
5. Pháp lý Việt Nam khi chuyển sang tiền thật. Ngoài phạm vi kế hoạch này.

## Câu hỏi còn mở
1. Nguồn lịch tin lớn (NFP/CPI/FOMC) cho biến thể "đóng lệnh trước tin 08:30". Đề xuất: CSV tự soạn từ lịch công bố chính thức của BLS/Fed.
2. Ngưỡng đi tiếp/dừng ở giai đoạn 6 là đề xuất của mình. Bạn chấp nhận hay muốn chỉnh?
3. Có cần lệnh Telegram `/stop` để dừng khẩn cấp ở giai đoạn 8 không? Hiện kế hoạch dùng cờ trong file cấu hình.
