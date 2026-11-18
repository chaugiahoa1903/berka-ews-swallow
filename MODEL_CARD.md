# Model card: Swallow early-warning model (bản nháp)

> Replay dữ liệu Berka (PKDD'99), không phải hệ thống chạy thật. Model chưa từng được dùng hay kiểm chứng trên danh mục tín dụng thật. Phần bối cảnh pháp lý chỉ là bối cảnh nghiên cứu, không phải tuyên bố tuân thủ.

## 1. Tóm tắt

| Mục | Nội dung |
|---|---|
| Loại model | Logistic regression, regularization L2, đặc trưng đã chuẩn hóa |
| Nhiệm vụ | Chấm điểm theo tháng sau giải ngân: khoản vay này có khả năng sắp vỡ nợ không (cảnh báo sớm) |
| Đơn vị | Khoản vay, chấm tại một mốc as-of mỗi tháng |
| Tệp model | `models/lr_core_train1993_96.joblib` (huấn luyện trên khoản giải ngân 1993-96) |
| Siêu tham số | C = 0,001 (chọn bằng forward-chaining + quy tắc 1 sai số chuẩn), ngưỡng cảnh báo t = 0,1841 |
| Mã nguồn | `src/lr_lib.py`, `src/train_final.py`, `src/score_month.py` |
| Trạng thái | Nguyên mẫu portfolio, chạy trên replay dữ liệu mô phỏng |

## 2. Mục đích sử dụng

**Dự kiến:** minh họa một quy trình giám sát rủi ro liên tục: chấm điểm khoản vay đã giải ngân mỗi tháng, đưa danh sách cảnh báo (mới và đang tiếp diễn) cho người xem xét. Chỉ là tín hiệu ưu tiên để con người kiểm tra thêm.

**Ngoài phạm vi, không nên dùng cho:** quyết định duyệt hoặc từ chối vay; định giá; bất kỳ quyết định tự động nào về một con người cụ thể; áp dụng cho ngân hàng, giai đoạn hay thị trường khác Berka mà chưa kiểm chứng lại.

## 3. Dữ liệu

- **Nguồn:** Berka (PKDD'99), 8 bảng (account, client, disp, trans, order, loan, card, district) từ kho quan hệ CTU. Bản CTU đã làm sạch một phần (ngày là DATE, ngày sinh và giới tính đã giải mã).
- **Khoản vay:** 682, trong đó 606 "tốt" và 76 "xấu" (status B hoặc D). Trạng thái: A 203, B 31, C 403 (còn chạy, đúng hạn), D 45 (còn chạy, đang nợ).
- **Sự kiện vỡ nợ đại diện:** thiếu ít nhất 2 kỳ trả góp (`UVER`). Cảnh báo hợp lệ nếu xảy ra ở tháng trước sự kiện.
- **Mẫu đủ điều kiện:** khoản giải ngân từ 1997 trở về trước, bỏ 16 khoản xấu không có mốc (`label_ambiguous`): 11.455 dòng khoản-tháng, 511 khoản vay. Khoản giải ngân 1998 bị loại.
- **Hạn chế dữ liệu:** chỉ có khoản vay đã được duyệt (không có hồ sơ bị từ chối). Một số bất thường chưa giải thích: 30/682 khoản vay có chủ dưới 18 tuổi lúc vay; số tiền lãi `UROK` lệch ±1 ở khoảng 21% dòng.

## 4. Đặc trưng (bộ core, 10)

Tính tại mốc as-of, chỉ dùng lịch sử đến ngày đó, bỏ các dòng trả nợ `UVER`:

| Đặc trưng | Ý nghĩa |
|---|---|
| `ever_neg` | Số dư tài khoản từng âm đến mốc as-of |
| `hist_neg_share` | Tỷ lệ giao dịch lịch sử có số dư âm (tính theo số giao dịch, không theo thời gian) |
| `hist_penalty_cnt` | Số giao dịch `SANKC. UROK` (lãi phạt khi số dư âm) |
| `hist_bal_avg` | Số dư trung bình lịch sử |
| `loan_burden` | Khoản trả góp hằng tháng so với dòng tiền vào trung bình hằng tháng trong lịch sử |
| `lm_credit_ratio`, `lm_debit_ratio` | Dòng tiền vào / ra của tháng dương lịch gần nhất so với trung bình lịch sử (0/0 đặt bằng 1,0) |
| `loan_amount`, `loan_duration` | Điều khoản khoản vay |
| `loan_age_k` | Số tháng kể từ giải ngân (xem hạn chế: đây là hiện vật cách dựng nhãn) |

Giới tính và tuổi **không** nằm trong model mặc định; chỉ được thêm vào bản `demo` để so sánh.

## 5. Cách huấn luyện và đánh giá

- **Tách tập:** forward-chaining theo năm giải ngân (fold 1: train 1993-95, test 1996; fold 2: train 1993-96, test 1997). Không dùng tách ngẫu nhiên.
- **Chọn L2:** lưới log 13 điểm (1e-4 đến 1e2), validation forward-chaining, log-loss, quy tắc 1 sai số chuẩn; cả hai fold chọn C = 0,001, không nằm ở biên lưới.
- **Ngưỡng:** chọn từ validation với **giả định** chi phí "tối đa 1% khoản âm bị báo nhầm" (đây là giả định, không phải kết quả thống kê). t = 0,1841 cho model cuối.
- **Khoảng tin cậy:** Clopper-Pearson chính xác cho tỷ lệ; bootstrap 2.000 lần theo khoản vay cho lead time và AUC.
- **Mức trung thực:** bộ đặc trưng chốt sau khi đã thấy kết quả baseline trên test (không tinh chỉnh theo test). Phân tích `compare_models` và `silent_group_check` là khám phá.

## 6. Kết quả (test gộp 1996+1997: 34 khoản dương, 270 khoản âm)

| | Phát hiện / dương | Recall (CI 95%) | Báo nhầm / âm | Lead median |
|---|---|---|---|---|
| Luật "số dư từng âm" | 22/34 | 0,65 [0,46; 0,80] | 0/270 (cận trên 1,4%) | 1,5 tháng |
| Model L2 (core) | 23/34 | 0,68 [0,49; 0,83] | 0/270 (cận trên 1,4%) | 1,0 tháng |

- Chênh 1 khoản giữa luật và model không có ý nghĩa thống kê. 11/34 khoản dương không bị bắt bởi cả hai.
- Lead tối đa khả dụng (median) là 3 tháng; cảnh báo chỉ dùng khoảng 1 đến 1,5 tháng.
- AUC cấp dòng: 0,836 [0,714; 0,943] (fold 1), 0,874 [0,800; 0,952] (fold 2). Không gần 1: không có dấu hiệu leakage kiểu "hoàn hảo".
- Recall phụ thuộc định nghĩa mốc: khoảng 50% đến 65% (thiếu ít nhất 1 hay ít nhất 2 kỳ). Với 34 khoản dương, khoảng tin cậy rộng khoảng ±17 điểm phần trăm.
- **Độ nhạy:** kết luận "luật ≈ model" giữ nguyên với tham số H = 2, 6, 13, với mốc "thiếu ít nhất 1 kỳ" và khi loại chủ dưới 18 tuổi. Bản chỉ A/B có 7 khoản dương nên không kết luận được. Bản nhãn huấn luyện nghiêm ngặt (V7) suy biến và không được diễn giải.
- **Replay 23 tháng** (1997-02 đến 1998-12): các cảnh báo trúng 15 khoản dương, 0 khoản âm và 8 khoản xấu không có mốc; khớp với test 1997.

## 7. Giải thích

Hệ số chuẩn hóa ổn định dấu (≥ 0,99 qua bootstrap huấn luyện lại, cả hai fold): `ever_neg` (dương, lớn nhất), `hist_neg_share`, `hist_penalty_cnt`, `loan_burden` (dương), `loan_age_k` (âm). C = 0,001 co mạnh nên đọc hướng và độ ổn định, không đọc độ lớn. Đây là tương quan trong dữ liệu, không phải nhân quả. Mỗi cảnh báo kèm `top_drivers` (đóng góp chuẩn hóa vào điểm).

## 8. Công bằng

Chạy model có và không có giới tính, tuổi: recall không đổi (23/34), chênh AUC theo cặp là -0,045 [-0,106; 0,003] và +0,011 [-0,012; 0,031]. Kết luận: **chưa thấy bằng chứng** nhân khẩu học thêm giá trị, không phải đã chứng minh không có. Đây **không** phải kiểm tra công bằng: chưa xét biến đại diện (proxy), chưa đo khác biệt tỷ lệ báo nhầm theo nhóm, và 34 khoản dương không đủ sức phát hiện hiệu ứng nhỏ.

## 9. Hạn chế đã biết

1. **Thiên lệch chọn mẫu.** Không khoản vay tốt nào từng có số dư âm (0/606) trong khi 5,6% tài khoản không vay từng âm: gợi ý ngân hàng đã sàng lọc người vay. Không chứng minh được vì không có hồ sơ bị từ chối. Con số "0 báo nhầm" vì vậy không nên đọc là "không bao giờ báo nhầm".
2. **Rất ít mẫu dương** (34 trong test): không phân biệt được recall 50% và 80%.
3. **Kẽ hở nhãn theo thời gian chưa kiểm chứng** (V7 suy biến).
4. **`loan_age_k` là hiện vật cách dựng nhãn** (dòng dương chỉ có trước mốc, dòng âm kéo dài tới 60 tháng), không phải hành vi khách hàng. Giá trị của model trong nhóm khoản mà luật không báo chưa chứng minh được.
5. **Chưa kiểm tra công bằng** đầy đủ; một nguồn dữ liệu, một ngân hàng, một thời kỳ.
6. **Khoảng một phần ba** khoản vỡ nợ (11/34) không có tín hiệu số dư âm và không bị bắt.
7. **Chưa kiểm định hiệu chuẩn (calibration)** của điểm số; không nên đọc điểm như xác suất thật.

## 10. Giám sát và vận hành (trong replay)

Mỗi tháng: kiểm tra chất lượng dữ liệu (lỗi thì dừng), chấm điểm, ghi `mart.alerts` (không chứa nhãn), tách cảnh báo mới và tiếp diễn, bản tin do LLM viết rồi bị kiểm tra: mọi số phải có trong báo cáo cảnh báo, không đạt thì thay bằng bản tin do code dựng. Kiểm tra này bắt số sai, không bắt nghĩa sai. Chưa có theo dõi trôi dữ liệu (drift) hay hiệu chuẩn theo thời gian.

## 11. Bối cảnh nghiên cứu (không phải tuyên bố tuân thủ)

Các hướng quản trị đang được thảo luận: dự thảo quy định quản trị AI của Ngân hàng Nhà nước, Thông tư 46/2026/TT-NHNN về sự đồng ý khi chia sẻ dữ liệu tín dụng, EU AI Act xếp chấm điểm tín dụng là rủi ro cao, SR 26-2 ở Mỹ. Dự án này không thực thi nghĩa vụ nào trong số đó. Nếu áp dụng thật cần có cơ sở đồng ý dữ liệu, rà soát công bằng, tài liệu hóa và giám sát độc lập.

## 12. Phiên bản

Bản nháp, 18/11/2026. Số liệu lấy từ `reports/*.txt`, `results.md`, `sensitivity.md` của dự án.
