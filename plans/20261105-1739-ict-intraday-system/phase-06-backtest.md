# Giai đoạn 6: Backtest và quyết định đi tiếp/dừng

Ngày: 2026-11-05 · Ưu tiên: cao · Phụ thuộc: giai đoạn 5 · Trạng thái: chưa bắt đầu · Review: chưa

Tổng quan: [plan.md](plan.md) · Trước: [giai đoạn 5](phase-05-model-and-risk.md) · Sau: [giai đoạn 7](phase-07-live-signals.md)

## Mục tiêu
Mô phỏng các lệnh trên M1 một cách thận trọng, có tính phí. Chọn **một** cấu hình trên dữ liệu IS, kiểm tra **một lần** trên OOS, rồi ra quyết định đi tiếp hay dừng. Đây là **điểm kiểm soát bắt buộc**.

## Chia dữ liệu
- **IS (in-sample):** 2020-01 → 2023-12. Dùng để chọn biến thể.
- **OOS (out-of-sample):** 2024-01 → 2026-10. Bị khóa: lệnh backtest từ chối chạy OOS nếu không có `--final`. Mỗi lần chạy `--final` được ghi vào `reports/oos-runs.log`.
- Kiểm tra độ ổn định trên IS: walk-forward theo năm. Chạy cấu hình được chọn trên từng năm 2020, 2021, 2022, 2023. Không được có năm nào lỗ nặng (< –10R).

## Mô phỏng khớp lệnh (`fills.py`, dùng M1 bid/ask)
- Lệnh limit long khớp khi `ask_low ≤ entry`, short khi `bid_high ≥ entry`. Chỉ xét từ nến M1 **sau** `created_at`.
- Lệnh chờ bị hủy khi đến `valid_until`, hoặc khi giá chạm TP trước khi khớp (setup đã chạy mất).
- SL và TP cùng bị chạm trong **một nến M1** thì **tính là SL** (giả định thận trọng). Đếm số ca này trong báo cáo.
- Giá vượt qua SL thì thoát tại giá mở nến (slippage xấu), không thoát tại giá SL.
- Đến 12:00 NY thì đóng lệnh theo giá đóng cửa M1 phía thoát (bid cho long, ask cho short).
- Biến thể `flat_before_news`: không vào lệnh và đóng lệnh lúc T–5 phút trước tin lớn. Nguồn là `data/calendar/high_impact.csv` (`ts_utc, currency, event`). Phải soạn CSV trước, xem câu hỏi mở.
- Phí: `extra_spread_pips` (spread broker trừ spread Dukascopy, mặc định 0.3 pip) và `commission_per_lot_roundtrip` (mặc định 7 USD/lot). Có chạy độ nhạy với spread ×1.5.

## Chỉ số (`metrics.py`) theo từng mã, phiên, năm và tổng
Số lệnh, tỷ lệ thắng, R trung bình, kỳ vọng (R và USD), profit factor, max drawdown (theo % equity, khi mô phỏng với vốn 100 USD), chuỗi thua dài nhất, % lệnh đóng theo giờ, % ca SL và TP cùng nến, số tín hiệu bị bỏ do lot < min, lợi nhuận theo tháng.

## Tiêu chí đi tiếp/dừng (đề xuất, cần bạn duyệt)
Đi tiếp sang giai đoạn 7 khi trên **OOS** (EURUSD + GBPUSD gộp) đạt **tất cả**:
1. ≥ 100 lệnh.
2. Kỳ vọng ≥ +0.15R mỗi lệnh sau phí, và vẫn > 0 khi spread ×1.5.
3. Max drawdown ≤ 25% với rủi ro thực tế.
4. Kỳ vọng OOS cùng dấu và ≥ 50% kỳ vọng IS (không suy giảm mạnh).
5. Không có tháng nào đóng góp > 30% tổng lợi nhuận.

Không đạt thì **dừng**. Không chỉnh tiếp trên OOS. Có thể quay lại giai đoạn 5 với **ý tưởng mới** (không chỉ đổi tham số) và dùng một vùng OOS mới khi có thêm dữ liệu.

## Vàng (chỉ tính điều kiện mở khóa)
Chạy cấu hình được chọn trên XAUUSD IS. Ghi lại SL trung vị (USD/0.01 lot) và vốn tối thiểu = SL trung vị ÷ 2%. Không dùng kết quả này để chọn cấu hình FX.

## File (đề xuất)
| Đường dẫn | Hành động |
|---|---|
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/backtest/engine.py` | tạo (duyệt theo thời gian: model → risk → fills) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/backtest/fills.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/backtest/metrics.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/backtest/report.py` | tạo (Markdown + HTML equity curve) |
| `/Users/nhhai7/LocalData/TVTools/data/calendar/high_impact.csv` | tạo (do bạn hoặc mình soạn) |
| `/Users/nhhai7/LocalData/TVTools/tests/backtest/` | tạo |

## Các bước
1. `fills.py` theo TDD. Mỗi quy tắc khớp lệnh ở trên có ít nhất một test với nến M1 dựng bằng tay.
2. `engine.py`: duyệt nến M5 theo thời gian, gọi model, risk, rồi fills trên M1. Lưu danh sách lệnh vào Parquet.
3. `metrics.py`, `report.py`.
4. Quét 32 tổ hợp trên IS. Xếp hạng theo kỳ vọng sau phí, có kèm số lệnh. Chọn cấu hình **đơn giản nhất** nằm trong nhóm tốt. Ghi lý do chọn.
5. Walk-forward theo năm trên IS.
6. Chạy OOS **một lần** với `--final`. Viết `reports/backtest-decision.md`: số liệu, so với tiêu chí, kết luận.
7. Tính điều kiện mở khóa vàng.

## Việc cần làm
- [ ] Fills + test
- [ ] Engine + lưu lệnh
- [ ] Metrics + report
- [ ] Lịch tin lớn (CSV)
- [ ] Quét 32 tổ hợp IS + chọn cấu hình
- [ ] Walk-forward IS
- [ ] OOS một lần + báo cáo quyết định
- [ ] Ngưỡng vốn cho vàng

## Tiêu chí chấp nhận
- `uv run pytest tests/backtest` qua.
- Có `reports/backtest-decision.md` với đủ chỉ số và kết luận rõ ràng là đi tiếp hay dừng.
- Bạn duyệt kết luận.
- Đối chiếu bằng tay: chọn 10 lệnh ngẫu nhiên, mở chart (`review --signals --allow-oos`) và xác nhận vào lệnh, thoát lệnh, PnL đúng.

## Rủi ro
- **Data snooping:** 32 tổ hợp trên IS vẫn là tìm kiếm. Vì vậy OOS chỉ chạy một lần, và tiêu chí 4 kiểm tra mức suy giảm.
- **Lạc quan về khớp lệnh:** lệnh limit tại cạnh FVG trên thị trường thật có thể không khớp nếu giá chỉ chạm sát. Có biến thể yêu cầu giá vượt qua entry 0.2 pip mới tính là khớp.
- **Ít lệnh:** khoảng 1 setup/phiên/mã ở mức tối đa, sau khi lọc có thể chỉ 100–300 lệnh/năm. Nếu OOS < 100 lệnh thì kết luận là "chưa đủ dữ liệu", không phải "đi tiếp".
