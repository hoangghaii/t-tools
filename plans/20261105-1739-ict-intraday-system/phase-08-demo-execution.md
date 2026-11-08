# Giai đoạn 8: Tự đặt lệnh trên tài khoản demo

Ngày: 2026-11-05 · Ưu tiên: trung bình · Phụ thuộc: giai đoạn 7 (chạy thử đạt, bạn duyệt) · Trạng thái: chưa bắt đầu · Review: chưa

Tổng quan: [plan.md](plan.md) · Trước: [giai đoạn 7](phase-07-live-signals.md)

## Mục tiêu
Runner tự đặt, hủy và đóng lệnh trên **cTrader demo** theo tín hiệu. Mọi trạng thái được đối chiếu với broker. Giai đoạn này **không** dùng tài khoản tiền thật. Chuyển sang tiền thật là một quyết định riêng, sau khi cân nhắc rủi ro pháp lý tại Việt Nam.

## Thiết kế
- Giao diện `Broker`: `place_limit(signal, lot) -> order_id`, `cancel(order_id)`, `close_position(position_id)`, `open_orders()`, `open_positions()`, `deals_since(ts)`, `account_equity()`.
- **SL và TP luôn được gắn sẵn trên lệnh ở phía broker.** Nhờ vậy, nếu runner chết thì lệnh vẫn có SL/TP. **Cần xác minh** cTrader `ProtoOANewOrderReq` chấp nhận `stopLoss`/`takeProfit` tuyệt đối cho lệnh limit. Nếu không: đặt SL/TP ngay sau khi lệnh khớp (`ProtoOAAmendPositionSLTPReq`). Trong trường hợp đó, khoảng thời gian chưa có SL là một rủi ro cần đo.
- **Idempotency:** `label`/`clientOrderId` = `signal_id`. Trước khi đặt lệnh, kiểm tra xem đã có lệnh với label đó chưa. Không bao giờ đặt trùng.
- **Đối chiếu khi khởi động và mỗi 5 phút:** so trạng thái SQLite với broker. Lệnh hoặc vị thế lạ (không có label của hệ thống) thì báo động và **không động vào**.
- Giới hạn rủi ro tính từ **dữ liệu broker** (deals, equity), không chỉ từ trạng thái nội bộ.
- **Đóng theo giờ:** 11:00 NY hủy lệnh chờ, 12:00 NY đóng vị thế. Nếu runner không chạy lúc đó thì watchdog báo động. Lần khởi động tiếp theo sẽ đóng ngay các vị thế quá giờ.
- **Công tắc dừng:** `trading_enabled = false` trong config, **hoặc** có file `STOP` trong thư mục dự án. Khi đó runner chỉ gửi tín hiệu, không đặt lệnh mới, nhưng vẫn quản lý lệnh đang mở.
- **Kiểm tra trước khi đặt lệnh:** account ID phải là **demo** (lấy từ API). Gặp tài khoản live thì dừng hẳn, trừ khi có cờ cấu hình `allow_live = true`. Cờ này không được thêm trong giai đoạn này.
- Gửi Telegram cho mọi sự kiện: đặt lệnh, khớp, SL, TP, hủy, đóng theo giờ, lỗi.

## File (đề xuất)
| Đường dẫn | Hành động |
|---|---|
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/live/broker.py` | tạo (giao diện + `PaperBroker` dùng `fills.py` để test) |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/live/broker_ctrader.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/live/reconcile.py` | tạo |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/live/runner.py` | sửa (gọi broker sau risk) |
| `/Users/nhhai7/LocalData/TVTools/tests/live/test_execution.py` | tạo (dùng `PaperBroker` và broker giả có lỗi được tiêm vào) |

## Các bước
1. Xác minh API: SL/TP trên lệnh limit, cách dùng label, reconcile request. Ghi lại trong docstring kèm link tài liệu.
2. `Broker` + `PaperBroker`, test các luồng chuẩn.
3. Test lỗi:
   - Mất kết nối giữa lúc đặt lệnh và lúc nhận xác nhận (đặt lại không được tạo lệnh trùng).
   - Runner khởi động lại khi đang có vị thế.
   - Khởi động sau 12:00 NY mà còn vị thế.
   - Broker từ chối lệnh (volume, giá).
4. `CTraderBroker`. Test live trên demo bằng một lệnh limit nhỏ đặt xa giá, rồi hủy.
5. Bật tự đặt lệnh trên demo. Chạy ≥ 4 tuần.

## Việc cần làm
- [ ] Xác minh API đặt lệnh
- [ ] `Broker` + `PaperBroker` + test luồng chuẩn
- [ ] Test lỗi và khôi phục
- [ ] `CTraderBroker` + test live demo
- [ ] Công tắc dừng + kiểm tra tài khoản demo
- [ ] Chạy demo ≥ 4 tuần

## Tiêu chí chấp nhận
- `uv run pytest` qua, gồm các ca lỗi.
- 4 tuần trên demo:
  - 100% tín hiệu hợp lệ tạo đúng một lệnh.
  - 0 lệnh trùng.
  - 0 vị thế giữ qua 12:00 NY mà không có báo động.
  - Mọi lần đối chiếu đều khớp.
- Giá khớp thật so với mô phỏng: chênh trung bình ≤ 0.3 pip. Ghi vào `reports/demo-execution.md`.

## Rủi ro và cách lùi lại
- Lỗi đặt lệnh trùng hoặc lệnh không có SL là rủi ro nghiêm trọng nhất. Đã có idempotency, SL gắn trên lệnh và reconcile. Cách lùi lại: tạo file `STOP`, rồi đóng tay trên cTrader.
- Chuyển sang tiền thật **ngoài phạm vi**. Cần: một kế hoạch riêng, VPS, và bạn tự đánh giá rủi ro pháp lý cùng việc nạp/rút tiền tại Việt Nam.
