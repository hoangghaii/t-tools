# Giai đoạn 7: Tín hiệu trực tiếp qua Telegram (dữ liệu cTrader demo)

Ngày: 2026-11-05 · Ưu tiên: trung bình · Phụ thuộc: giai đoạn 6 (đạt điều kiện đi tiếp) · Trạng thái: chưa bắt đầu · Review: chưa

Tổng quan: [plan.md](plan.md) · Trước: [giai đoạn 6](phase-06-backtest.md) · Sau: [giai đoạn 8](phase-08-demo-execution.md)

## Mục tiêu
Chạy model trên dữ liệu trực tiếp từ broker, gửi tín hiệu qua Telegram. Kết quả của từng tín hiệu được theo dõi tự động (chạy thử, chưa đặt lệnh). Kiểm tra dữ liệu broker có khớp với Dukascopy không. Đây là **điểm kiểm soát bắt buộc** trước giai đoạn 8.

## Bối cảnh (từ báo cáo researcher, 2026-11-05)
- SDK `ctrader-open-api` 0.9.2 chạy trên Twisted, hỗ trợ Python ≤ 3.12. Host demo: `demo.ctraderapi.com`, cổng 5035 (protobuf) và 5036 (JSON).
- OAuth2: đăng ký app bằng cTrader ID, scope `trading` (cần cho giai đoạn 8) hoặc `accounts`. Access token sống khoảng 30 ngày, refresh token không hết hạn.
- Giới hạn tốc độ: dữ liệu lịch sử 5 yêu cầu/giây. Nến M1 mỗi lần khoảng 2 tuần (theo báo cáo cộng đồng, chưa xác nhận). Tải theo đoạn và lưu lại.
- Đọc `minVolume`, `stepVolume`, `lotSize` của từng mã từ API. Không ghi cứng.

## Kiến trúc
- `DataSource` (giao diện): `get_m1(symbol, start, end)`, `get_symbol_spec(symbol)`. Có hai bản cài đặt: `DukascopySource` và `CTraderSource`.
- `CTraderSource` chạy Twisted reactor trong một **luồng riêng**, và có hàm đồng bộ cho phần còn lại của code. Twisted không được lan ra ngoài module này. Nếu SDK lỗi hoặc không ổn: viết lại bằng WebSocket JSON (cổng 5036), giữ nguyên giao diện.
- `runner.py`: trong các cửa sổ 01:30–12:05 NY ngày thường, mỗi phút sau khi M1 đóng:
  1. Lấy các nến M1 mới.
  2. Resample.
  3. Tính lại detector trên cửa sổ trượt (10 ngày giao dịch).
  4. `model.on_bar`, rồi `risk`.
  5. Có Signal mới thì lưu SQLite và gửi Telegram.
- **Theo dõi kết quả:** mỗi tín hiệu được mô phỏng bằng chính `fills.py` trên dữ liệu M1 trực tiếp (vào lệnh, SL/TP, đóng 12:00 NY). Ghi kết quả vào SQLite.
- **Nhịp tim (heartbeat):** báo Telegram khi bắt đầu và kết thúc mỗi phiên. Báo động khi quá 3 phút không có nến mới trong giờ thị trường, hoặc khi mất kết nối.
- **Chạy trên Mac:** dùng `launchd` (file plist). `caffeinate -i` trong lúc chạy để Mac không ngủ. Log quay vòng tại `logs/`.

## Nội dung tin Telegram (giờ VN và giờ NY)
`[EURUSD] LONG · NY AM · 19:42 VN (07:42 NY)`, kèm entry, SL (pip), TP (R), lot 0.01, rủi ro USD, hiệu lực đến, và lý do (sweep Asia Low → MSS → FVG).

## Bảo mật
- Các biến `CTRADER_CLIENT_ID`, `CTRADER_CLIENT_SECRET`, `CTRADER_REFRESH_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` đặt trong `.env` với `chmod 600`. Không bao giờ in ra log.
- Bot chỉ **gửi** tin tới `TELEGRAM_CHAT_ID`. Giai đoạn này bot không nhận lệnh nào.
- Refresh token được lưu lại khi xoay vòng (ghi file nguyên tử).

## File (đề xuất)
| Đường dẫn | Hành động |
|---|---|
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/data/source.py` | tạo (giao diện `DataSource`) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/data/ctrader.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/live/runner.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/live/telegram.py` | tạo (HTTP Bot API qua `httpx`) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/live/storage.py` | tạo (SQLite: signals, outcomes, heartbeats) |
| `/Users/nhhai7/LocalData/TVTools/scripts/ctrader_auth.py` | tạo (lấy refresh token qua OAuth, chạy 1 lần) |
| `/Users/nhhai7/LocalData/TVTools/deploy/com.tvtools.runner.plist` | tạo |
| `/Users/nhhai7/LocalData/TVTools/tests/live/` | tạo (dùng `DataSource` giả và Telegram giả) |

## Các bước
1. Bạn: mở cTrader demo (số dư 100 USD), đăng ký Open API app, tạo bot Telegram. Mình viết hướng dẫn từng bước.
2. `scripts/ctrader_auth.py` → lưu refresh token.
3. `CTraderSource`: spec của mã, M1 lịch sử theo đoạn. Test tích hợp đánh dấu `@pytest.mark.live`, mặc định bỏ qua trong CI.
4. **Kiểm tra dữ liệu broker:** tải 3 tháng gần nhất từ cTrader, so với Dukascopy (độ lệch giá, spread theo giờ). Chạy lại backtest 3 tháng trên dữ liệu broker. Kỳ vọng phải không lệch quá 0.1R mỗi lệnh. Ghi vào `reports/broker-data-check.md`.
5. `runner`, `telegram`, `storage`, heartbeat. Test bằng cách phát lại một ngày lịch sử qua `DataSource` giả.
6. **Đối chiếu hằng ngày:** sau 12:05 NY, chạy lại ngày đó bằng engine backtest. Tín hiệu phải **trùng 100%** với tín hiệu chạy thật. Lệch thì báo Telegram.
7. Chạy thử ≥ 6 tuần hoặc ≥ 30 tín hiệu, lấy mốc đến sau.

## Việc cần làm
- [ ] Hướng dẫn cài đặt tài khoản (cTrader, Telegram)
- [ ] OAuth script
- [ ] `CTraderSource` + test live
- [ ] Báo cáo so sánh dữ liệu broker với Dukascopy
- [ ] Runner + Telegram + SQLite + heartbeat
- [ ] Đối chiếu hằng ngày
- [ ] launchd + caffeinate
- [ ] Chạy thử ≥ 6 tuần / ≥ 30 tín hiệu

## Tiêu chí chấp nhận
- `uv run pytest` qua (test live được bỏ qua mặc định). Chạy `uv run pytest -m live` qua khi có token.
- Báo cáo dữ liệu broker đạt (lệch ≤ 0.1R mỗi lệnh).
- Đối chiếu hằng ngày trùng 100% trong suốt thời gian chạy thử.
- Kết quả chạy thử không tệ hơn rõ rệt so với OOS. Ví dụ: kỳ vọng không thấp hơn OOS quá 2 sai số chuẩn. Bạn duyệt `reports/forward-test.md`.

## Rủi ro
- Mac ngủ, mất mạng hoặc mất điện thì bỏ lỡ tín hiệu. Heartbeat sẽ báo. Chấp nhận được ở giai đoạn chỉ gửi tín hiệu. VPS giải quyết sau.
- SDK lỗi trên Python 3.12: chuyển sang WebSocket JSON.
- Broker từ chối khách Việt Nam: thử broker khác có cTrader (FxPro, FP Markets). Code không phải đổi.
