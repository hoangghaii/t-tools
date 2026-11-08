# Giai đoạn 1: Khung dự án và kiểu dữ liệu lõi

Ngày: 2026-11-05 · Ưu tiên: cao · Phụ thuộc: không · Trạng thái: hoàn thành 2026-11-06 · Review: đã tự rà soát

Tổng quan: [plan.md](plan.md)

## Mục tiêu
Tạo khung dự án Python có thể chạy được. Định nghĩa các kiểu dữ liệu và tiện ích thời gian mà mọi giai đoạn sau dùng chung. Phần thời gian là chỗ dễ sai nhất (DST, ngày giao dịch), nên được làm và test trước.

## Bối cảnh
- Máy: macOS arm64, Python hệ thống 3.14, **chưa có `uv`**, chưa có Python 3.12. SDK cTrader chỉ hỗ trợ đến 3.12, nên cố định 3.12 ngay từ đầu.
- Dự án chưa là git repo.

## File (tất cả là đề xuất, chưa tồn tại)
| Đường dẫn | Hành động | Lý do |
|---|---|---|
| `/Users/nhhai7/LocalData/TVTools/pyproject.toml` | tạo | `requires-python = ">=3.12,<3.13"`, phụ thuộc, cấu hình ruff/mypy/pytest |
| `/Users/nhhai7/LocalData/TVTools/.python-version` | tạo | `3.12` cho uv |
| `/Users/nhhai7/LocalData/TVTools/.gitignore` | tạo | `data/`, `reports/`, `.env`, `.venv/`, `__pycache__/` |
| `/Users/nhhai7/LocalData/TVTools/.env.example` | tạo | Tên biến bí mật (không có giá trị) |
| `/Users/nhhai7/LocalData/TVTools/config/default.toml` | tạo | Mã, phiên, rủi ro, tham số ICT |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/core/types.py` | tạo | `Bar`, `Direction`, `Horizon`, `Signal`, `Trade`, `TradeResult` |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/core/config.py` | tạo | Đọc TOML vào dataclass bất biến, kiểm tra giá trị |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/core/timeutil.py` | tạo | UTC↔NY, ngày giao dịch, cửa sổ phiên |
| `/Users/nhhai7/LocalData/TVTools/src/tvtools/cli.py` | tạo | `python -m tvtools` (argparse) |
| `/Users/nhhai7/LocalData/TVTools/tests/core/test_timeutil.py` | tạo | Các ca DST |
| `/Users/nhhai7/LocalData/TVTools/CLAUDE.md`, `AGENTS.md` | sửa | Phần "Current state" → các lệnh thật (ngoài khối agentkit) |

## Thiết kế
- **`Signal`** (frozen dataclass): `symbol, direction, horizon="intraday", model_id, variant_id, session, created_at (UTC), entry, stop_loss, take_profit, valid_until, invalidation_price, reason (dict các sự kiện dẫn tới tín hiệu)`. Có `risk_pips(spec)` và `rr()`.
- **`SymbolSpec`** trong config: `pip_size` (EURUSD 0.0001, XAUUSD 0.01 hoặc 0.1, chọn một quy ước và ghi rõ), `contract_size`, `min_lot`, `lot_step`, `enabled`. Trong chạy thật, giá trị đọc từ API sẽ ghi đè config.
- **Thời gian:** mọi timestamp là `pandas.Timestamp` có tz UTC. Dùng `zoneinfo.ZoneInfo("America/New_York")`. Không bao giờ dùng giờ VN trong logic. Giờ VN chỉ để hiển thị trong Telegram.
- **Ngày giao dịch:** bắt đầu 00:00 NY (theo ICT). Hàm `trading_day(ts_utc) -> date`.
- **Cửa sổ phiên:** khai báo bằng giờ NY trong config (`asia = 20:00–00:00` của ngày trước, `london_kz = 02:00–05:00`, `nyam_kz = 07:00–11:00`, `flat_by = 12:00`). Hàm `session_window(day, name) -> (start_utc, end_utc)`.
- **Bí mật:** chỉ đọc từ biến môi trường hoặc `.env`. Không ghi vào config TOML hay log.

## Các bước
1. Hỏi bạn: cài `uv` (`brew install uv`) và chạy `git init` (theo CLAUDE.md, chỉ làm khi bạn đồng ý).
2. `uv init --package` với Python 3.12, thêm phụ thuộc: `pandas pyarrow numpy plotly`. Phụ thuộc dev: `pytest ruff mypy pandas-stubs`.
3. Viết `timeutil.py` và test trước (TDD cho phần này).
4. Viết `types.py`, `config.py`, `config/default.toml`. Test: config sai (SL âm, lot < min) báo lỗi rõ ràng.
5. Viết `cli.py` với lệnh `version` để kiểm tra luồng chạy.
6. Cập nhật phần "Current state" trong CLAUDE.md và AGENTS.md với các lệnh thật.

## Việc cần làm
- [x] uv + Python 3.12 + venv
- [x] git init (theo yêu cầu triển khai Phase 1) + `.gitignore`
- [x] `timeutil` + test DST
- [x] `types`, `config`, `default.toml`
- [x] CLI tối thiểu
- [x] Cập nhật CLAUDE.md/AGENTS.md

## Bằng chứng hoàn thành (2026-11-06)
- `uv` 0.13.7, Python 3.12.16 từ Homebrew, `.venv/` và `uv.lock` được tạo. Tải Python bằng `uv python install` gặp lỗi chứng chỉ; bản Homebrew đáp ứng đúng phiên bản yêu cầu.
- `uv run pytest`: 10 passed; ca đơn lẻ `test_nyam_winter_and_summer`: 1 passed.
- `uv run ruff check .`: All checks passed. `uv run mypy src`: no issues found in 7 source files.
- `uv run python -m tvtools version`: `0.1.0`. `uv build --offline`: source distribution và wheel thành công; wheel có `tvtools/default.toml`.

## Tiêu chí chấp nhận
- `uv run pytest` qua. Các ca test bắt buộc:
  - 2026-11-02 (EST): `nyam_kz` = 12:00–16:00 UTC = 19:00–23:00 VN.
  - 2026-07-15 (EDT): `nyam_kz` = 11:00–15:00 UTC.
  - Ngày chuyển giờ 2026-03-08 và 2026-11-01: cửa sổ phiên không bị lệch hay trùng.
  - Phiên Á 20:00–00:00 NY thuộc về ngày giao dịch **sau**.
- `uv run ruff check .` và `uv run mypy src` sạch.
- `uv run python -m tvtools version` chạy được.

## Rủi ro
- Quy ước pip của XAUUSD không thống nhất giữa các broker. Lưu ý: chỉ dùng `pip_size` cho hiển thị và ngưỡng 20 pip của FX. Rủi ro tiền luôn tính bằng `khoảng_giá × contract_size × lot`.
