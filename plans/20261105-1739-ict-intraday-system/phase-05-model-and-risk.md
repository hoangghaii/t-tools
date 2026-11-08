# Giai đoạn 5: Mô hình Sweep → MSS → FVG và bộ lọc rủi ro

Ngày: 2026-11-05 · Ưu tiên: cao · Phụ thuộc: giai đoạn 3, 4 (tham số detector đã khóa) · Trạng thái: chưa bắt đầu · Review: chưa

Tổng quan: [plan.md](plan.md) · Trước: [giai đoạn 4](phase-04-visual-review.md) · Sau: [giai đoạn 6](phase-06-backtest.md)

## Mục tiêu
Ghép các sự kiện ICT thành **máy trạng thái** sinh ra `Signal`. Thêm bộ lọc rủi ro cấp tài khoản. Cả hai phải dùng **cùng một code** cho backtest và chạy thật.

## Máy trạng thái (mỗi mã, mỗi phiên)
```
IDLE ──(trong killzone, sweep một mức liquidity hợp lệ)──▶ SWEPT
  hướng lệnh = ngược phía bị sweep (sweep đáy → tìm lệnh long)
SWEPT ──(MSS cùng hướng trong mss_max_bars)──▶ ARMED
SWEPT ──(hết killzone | hết mss_max_bars)──▶ IDLE
ARMED ──(có FVG trong chặng displacement, giữa sweep và nến MSS)──▶ phát Signal ▶ DONE
ARMED ──(giá vượt cực trị của sweep | hết killzone)──▶ IDLE
```
- Mức liquidity hợp lệ:
  - London: Asia H/L, PDH/PDL, equal H/L.
  - NY AM: thêm London H/L.
- `Signal`:
  - `entry` là lệnh limit tại cạnh gần của FVG, hoặc CE (theo biến thể).
  - `stop_loss` = cực trị sweep ± (`sl_buffer_atr × ATR`).
  - `take_profit` chọn theo `tp_mode`.
  - `valid_until` = min(hết killzone, 11:00 NY).
- `max_setups_per_session = 1` (mặc định). Sau DONE, phiên đó không tìm setup mới nữa.
- Mọi quyết định của máy trạng thái chỉ đọc sự kiện có `confirmed_at ≤ closed_at` của nến hiện tại.

## Biến thể (giới hạn 32 tổ hợp để hạn chế overfitting)
| Trục | Giá trị |
|---|---|
| Cửa sổ | `full_kz` (London 02–05, NY AM 07–11) · `silver_bullet` (03–04, 10–11) |
| Vào lệnh | `fvg_edge` · `ce` |
| TP | `nearest_liq_ge_2r` (mức liquidity đối diện gần nhất cho ≥ 2R, không có thì bỏ) · `fixed_2r` |
| Bias | `none` · `h1_structure` (chỉ vào theo hướng phá cấu trúc H1 gần nhất) |
| Tin 08:30 NY | `ignore` · `flat_before_news` (không vào lệnh và đóng lệnh trước tin lớn 5 phút). Biến thể này ở giai đoạn 6 |

## Rủi ro (`risk.py`, có trạng thái, dùng chung)
- Tất cả mã đều định giá bằng USD và tài khoản là USD, nên không cần quy đổi tiền tệ. **Assert** điều này trong config.
- `risk_usd(lot) = (|entry − SL| + spread_dự_kiến) × contract_size × lot`.
- `lot = floor(equity × max_risk_pct / risk_usd(1) / lot_step) × lot_step`, kẹp trong `[min_lot, max_lot]`.
  - `max_lot`: FX 0.05, vàng 0.01.
  - Nếu kết quả < `min_lot` thì **bỏ tín hiệu** (ghi lý do).
  - Với vốn 100 USD, ngưỡng này tương đương SL ≤ 20 pip ở 0.01 lot.
  - (Ghi chú 2026-11-08) Giới hạn SL dùng **USD qua `max_risk_pct`** cho mọi mã. Bỏ `max_sl_pips_fx` trong `config/default.toml` và `RiskConfig` khi làm giai đoạn này. Pip XAUUSD = 0.1 USD (chỉ để hiển thị); 2 USD rủi ro ở 0.01 lot ứng với giá vàng đi 2 USD = 20 pip.
- Giới hạn tài khoản:
  - 1 lệnh mở (hoặc lệnh chờ) trên toàn tài khoản.
  - Sau 2 lệnh lỗ trong một ngày giao dịch thì dừng ngày đó.
  - Equity giảm –8% so với đầu tuần thì dừng đến tuần sau.
- `gold_unlocked(equity, median_gold_sl_usd, n_trades, expectancy)` → bool, dùng ở giai đoạn 7.

## File (đề xuất)
| Đường dẫn | Hành động |
|---|---|
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/models/base.py` | tạo (giao diện `Model.on_bar(ctx) -> list[Signal]`) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/models/sweep_mss_fvg.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/models/context.py` | tạo (gói sự kiện đã xác nhận đến thời điểm `t`) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/risk.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/tests/models/`, `tests/test_risk.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/viz/chart.py` | sửa (vẽ tín hiệu) |

## Các bước
1. `context.py`: lấy sự kiện đã tính sẵn và trả về view "những gì biết được tại `t`".
2. Máy trạng thái, viết theo TDD:
   - Mỗi chuyển trạng thái có một test với chuỗi sự kiện dựng bằng tay.
   - Có ca bị vô hiệu do hết killzone, và ca giá vượt cực trị sweep.
3. **Test đối chiếu batch với incremental.** Trên 2 tuần dữ liệu, so hai cách:
   - Tính detector một lần trên toàn bộ dữ liệu rồi chạy model.
   - Tính lại detector trên prefix ở mỗi nến M5.
   Hai cách phải sinh ra **cùng danh sách Signal**. Đây là bảo đảm cho câu "backtest = chạy thật".
4. `risk.py` + test: làm tròn lot, bỏ tín hiệu khi lot < min, giới hạn ngày/tuần, ranh giới tuần.
5. Vẽ tín hiệu lên chart. Lệnh `tvtools review --signals` để bạn xem 20 tín hiệu ngẫu nhiên trong IS.

## Việc cần làm
- [ ] Context theo thời gian
- [ ] Máy trạng thái + test chuyển trạng thái
- [ ] Các biến thể cấu hình được
- [ ] Test đối chiếu batch với incremental
- [ ] `risk.py` + test
- [ ] Vẽ tín hiệu + bạn xem 20 tín hiệu

## Tiêu chí chấp nhận
- `uv run pytest` qua toàn bộ, gồm test đối chiếu batch/incremental.
- `uv run mypy src` và `uv run ruff check .` sạch.
- Bạn xem 20 tín hiệu (IS) và xác nhận chúng là setup "đúng kiểu ICT" bạn muốn vào. Nếu không, quay lại sửa định nghĩa trước khi backtest.

## Rủi ro
- Chặng displacement có nhiều FVG. Quy tắc: chọn FVG **đầu tiên sau nến MSS hoặc chứa nến MSS**, gần giá nhất. Ghi rõ trong code và test.
- Sweep xảy ra ngay trước killzone. Quy tắc: chỉ tính sweep có `confirmed_at` nằm trong killzone. Có thể nới thành biến thể sau nếu bạn thấy cần.
