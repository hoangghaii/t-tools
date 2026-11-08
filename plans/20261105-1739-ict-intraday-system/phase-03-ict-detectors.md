# Giai đoạn 3: Bộ phát hiện khái niệm ICT

Ngày: 2026-11-05 · Ưu tiên: cao · Phụ thuộc: giai đoạn 2 · Trạng thái: chưa bắt đầu · Review: chưa

Tổng quan: [plan.md](plan.md) · Trước: [giai đoạn 2](phase-02-historical-data.md) · Sau: [giai đoạn 4](phase-04-visual-review.md)

## Mục tiêu
Viết các khái niệm ICT cần cho mô hình Sweep → MSS → FVG thành **hàm thuần túy, có tham số, không look-ahead**. Order block nằm ngoài phạm vi.

## Hợp đồng chung (quan trọng nhất)
- Đầu vào: DataFrame nến (bid) của một khung thời gian, cùng tham số.
- Đầu ra: DataFrame **sự kiện** với các cột `kind, direction, price | top/bottom, formed_at, confirmed_at, meta`.
- `confirmed_at` là thời điểm **sớm nhất** mà sự kiện có thể biết được chỉ từ nến đã đóng.
- Mọi ngưỡng tính theo **ATR(14) Wilder** của cùng khung, không dùng pip cố định. Nhờ vậy cùng code chạy được cho FX và vàng.
- Không đọc config toàn cục. Tham số được truyền vào hàm, để backtest quét được nhiều biến thể.

## Định nghĩa (mặc định có thể chỉnh sau giai đoạn 4)
| Khái niệm | Định nghĩa | `confirmed_at` | Tham số |
|---|---|---|---|
| ATR | Wilder 14 trên nến đã đóng | đóng nến | `atr_len=14` |
| Swing high/low | Fractal: `high[i]` lớn hơn hẳn `n` nến trái và ≥ `n` nến phải (đáy thì ngược lại) | đóng nến `i+n` | `swing_n=2` (M5) |
| Mức liquidity theo phiên | Đỉnh/đáy của phiên Á (20:00–00:00 NY), London KZ (02:00–05:00), ngày trước (PDH/PDL) | lúc phiên kết thúc | cửa sổ trong config |
| Equal highs/lows | ≥ 2 swing cách nhau ≤ `eq_tol × ATR`, trong `eq_lookback` nến | `confirmed_at` của swing sau | `eq_tol=0.1`, `eq_lookback=100` |
| Sweep | Nến có râu vượt mức L, rồi **đóng cửa quay lại** bên trong trong vòng `sweep_close_bars`. Đóng cửa vượt hẳn ra ngoài thì là "run", không phải sweep. Mỗi mức chỉ bị sweep một lần | đóng nến quay lại | `sweep_close_bars=1`, `min_pen=0` |
| Displacement | Thân nến ≥ `disp_k × ATR` và thân/biên độ ≥ `disp_body_ratio` | đóng nến | `disp_k=1.0`, `disp_body_ratio=0.6` |
| MSS | Sau sweep phía trên (bearish): nến đóng cửa dưới swing low gần nhất **đã được xác nhận trước** nến phá. Trong chặng phá phải có ít nhất 1 nến displacement. Phải xảy ra trong `mss_max_bars` sau sweep | đóng nến phá | `mss_max_bars=12` |
| FVG | Bullish: `high[1] < low[3]`, khoảng trống `[high[1], low[3]]`. Bearish thì ngược lại. CE = trung điểm. Kích thước ≥ `fvg_min × ATR` | đóng nến 3 | `fvg_min=0.1` |

Ghi chú: MSS chỉ dùng swing có `confirmed_at` < nến phá. Đây là chỗ look-ahead hay lọt vào nhất.

## File (đề xuất)
| Đường dẫn | Hành động |
|---|---|
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/ict/atr.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/ict/swings.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/ict/liquidity.py` | tạo (mức phiên, PDH/PDL, equal H/L) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/ict/sweep.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/ict/structure.py` | tạo (displacement, MSS) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/ict/fvg.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/ict/events.py` | tạo (schema sự kiện + kiểm tra cột) |
| `/Users/nhhai7/LocalData/TVTools/tests/ict/` | tạo (một file test cho mỗi detector + `test_prefix_invariance.py`) |

## Các bước
1. `events.py`: schema và hàm kiểm tra chung.
2. Mỗi detector viết theo TDD với chuỗi nến **dựng bằng tay** có kết quả biết trước. Ví dụ: 3 nến tạo FVG chính xác. Nến có râu vượt mức rồi đóng cửa quay lại thì là sweep, đóng cửa ngoài mức thì không phải sweep.
3. Ca biên: hòa giá (hai đỉnh bằng nhau) với swing; khoảng trống dữ liệu giữa phiên; đầu chuỗi khi ATR chưa đủ 14 nến (không phát sinh sự kiện).
4. **Test prefix invariance** trên dữ liệu test cố định (vài tuần M5 thật). Với 200 mốc thời gian `t` chọn ngẫu nhiên (có seed cố định), sự kiện tính trên `data[closed_at ≤ t]` và lọc `confirmed_at ≤ t` phải **bằng** sự kiện tính trên toàn bộ dữ liệu rồi lọc `confirmed_at ≤ t`.
5. Đo hiệu năng: chạy toàn bộ detector trên 1 năm M5 của 1 mã phải < 30 giây. Dùng vector hóa pandas/numpy. Chỉ dùng vòng lặp Python khi bắt buộc (sweep, MSS).

## Việc cần làm
- [ ] Schema sự kiện
- [ ] ATR, swings
- [ ] Liquidity (phiên, PDH/PDL, equal H/L)
- [ ] Sweep
- [ ] Displacement + MSS
- [ ] FVG
- [ ] Test prefix invariance cho **mọi** detector
- [ ] Đo hiệu năng

## Tiêu chí chấp nhận
- `uv run pytest tests/ict` qua, bao gồm prefix invariance cho tất cả detector.
- `uv run mypy src` và `uv run ruff check .` sạch.
- 1 năm M5 của 1 mã chạy < 30 giây trên Mac của bạn.

## Rủi ro
- Định nghĩa của máy khác với cách bạn nhìn chart. Giai đoạn 4 sẽ phát hiện và chỉnh. Tham số mặc định ở trên chỉ là điểm xuất phát.
- Quá nhiều tham số dẫn tới overfitting. Ở giai đoạn 6 chỉ quét tham số của mô hình. Tham số detector được **khóa** sau giai đoạn 4.
