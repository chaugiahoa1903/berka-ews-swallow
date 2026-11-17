-- sql/09_split_feasibility.sql - số khoản/dòng dương theo năm, để chọn mốc tách train/test và kỳ hạn cảnh báo
-- (1) theo năm giải ngân
SELECT YEAR(loan_date) AS loan_year, COUNT(*) AS loans, SUM(is_bad) AS bad,
       SUM(CASE WHEN is_bad = 1 AND event_k IS NOT NULL THEN 1 ELSE 0 END) AS bad_with_event
FROM clean.loan_event WHERE is_observable = 1
GROUP BY YEAR(loan_date) ORDER BY loan_year;
GO
-- (2) theo năm của mốc as-of: số dòng dùng được và số dòng dương với kỳ hạn 3 và 6 tháng
SELECT YEAR(as_of_date) AS as_of_year,
       SUM(CASE WHEN is_pre_event = 1 AND label_ambiguous = 0 THEN 1 ELSE 0 END) AS usable_rows,
       SUM(CASE WHEN is_pre_event = 1 AND label_ambiguous = 0 AND months_to_event BETWEEN 1 AND 3 THEN 1 ELSE 0 END) AS pos_rows_h3,
       COUNT(DISTINCT CASE WHEN is_pre_event = 1 AND label_ambiguous = 0 AND months_to_event BETWEEN 1 AND 3 THEN loan_id END) AS pos_loans_h3,
       SUM(CASE WHEN is_pre_event = 1 AND label_ambiguous = 0 AND months_to_event BETWEEN 1 AND 6 THEN 1 ELSE 0 END) AS pos_rows_h6,
       COUNT(DISTINCT CASE WHEN is_pre_event = 1 AND label_ambiguous = 0 AND months_to_event BETWEEN 1 AND 6 THEN loan_id END) AS pos_loans_h6
FROM clean.asof_grid GROUP BY YEAR(as_of_date) ORDER BY as_of_year;
GO
