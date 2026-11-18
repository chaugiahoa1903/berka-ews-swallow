# Từ điển chỉ số: `mart.alert_kpi_monthly`

Bảng này được tạo bởi `sql/21_alert_kpi_monthly.sql`, **chỉ tính từ `mart.alerts`**. Mỗi dòng là một tháng replay (`replay_month`, dạng `YYYY-MM`). Dữ liệu là replay Berka mô phỏng, không phải hệ thống chạy thật.

## Điều bảng này đo và không đo

- **Đo:** khối lượng và hành vi của cảnh báo theo tháng (số khoản được chấm, số cảnh báo, mới hay tiếp diễn, phân bố điểm). Đây là chỉ số **vận hành**, dùng để thấy hệ thống có chạy bình thường không.
- **Không đo:** độ chính xác. `mart.alerts` không chứa nhãn và kết quả thật, nên bảng này không cho biết cảnh báo có đúng không. Độ chính xác (recall, báo nhầm, lead time) được đo ở bước đánh giá riêng và ghi trong `results.md` và `README.md`.

## Các cột

| Cột | Định nghĩa | Ghi chú |
|---|---|---|
| `replay_month` | Tháng replay được chấm điểm | Tháng 1997-01 vắng mặt vì không qua kiểm tra chất lượng dữ liệu, nên không được ghi vào `mart.alerts` |
| `n_scored` | Số khoản vay được chấm điểm trong tháng | Số dòng của tháng đó trong `mart.alerts` |
| `n_alerts` | Số khoản có `alert = 1` (điểm vượt ngưỡng) | Ngưỡng cố định t = 0,1841 |
| `alert_rate` | `n_alerts / n_scored` | Tỷ lệ cảnh báo, không phải tỷ lệ vỡ nợ |
| `n_new` | Số cảnh báo mới: khoản vay có `alert = 1` lần đầu tiên ở tháng này | Cùng định nghĩa với `src/alert_report.py` |
| `n_continuing` | Số cảnh báo tiếp diễn: khoản có `alert = 1` và đã từng có `alert = 1` ở tháng trước (kể cả có tháng ngắt quãng) | `n_new + n_continuing = n_alerts` |
| `cum_loans_alerted` | Tổng số khoản vay đã từng bị cảnh báo đến hết tháng này | Cộng dồn của `n_new` |
| `n_ever_neg` | Số khoản được chấm có số dư từng âm đến mốc as-of (`ever_neg = 1`) | Số khoản mà luật "từng âm" sẽ báo |
| `n_ever_neg_not_alerted` | Trong đó số khoản có `ever_neg = 1` nhưng không bị cảnh báo (`alert = 0`) | Khoảng cách giữa luật và model trong tháng |
| `mean_score` | Điểm trung bình của các khoản được chấm | Điểm model, không phải xác suất đã hiệu chuẩn |
| `max_score` | Điểm cao nhất trong tháng | |
| `threshold` | Ngưỡng cảnh báo dùng trong tháng | Phải không đổi qua các tháng nếu dùng cùng một model |
| `n_model_files` | Số tệp model khác nhau đã chấm trong tháng | Mong đợi bằng 1; lớn hơn 1 nghĩa là tháng bị chấm bằng nhiều phiên bản model |
| `computed_at` | Thời điểm tạo bảng | |

## Kiểm tra đối chiếu sau khi tạo bảng

Câu truy vấn cuối của `sql/21_alert_kpi_monthly.sql` in một dòng đối chiếu, kết quả đúng là:

- `sum_n_new` bằng `loans_ever_alerted` (số khoản vay có ít nhất một cảnh báo).
- `months_in_kpi` bằng `months_in_alerts`.
- `alerts_unexplained` bằng 0 (mọi cảnh báo đều là mới hoặc tiếp diễn).
- `max_model_files_per_month` bằng 1.

## Hạn chế khi đọc các chỉ số

- Số khoản được chấm tăng dần theo thời gian vì replay chỉ chấm khoản giải ngân năm 1997, nên `alert_rate` và `n_alerts` cần đọc cùng với `n_scored`.
- `n_new` và `n_continuing` chỉ đúng khi các tháng trước đã được ghi thật vào `mart.alerts`.
- Đây là dữ liệu mô phỏng của một ngân hàng ở một thời kỳ; các chỉ số không cho biết gì về danh mục thật.
