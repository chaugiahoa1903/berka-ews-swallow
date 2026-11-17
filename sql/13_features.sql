-- sql/13_features.sql - đặc trưng as-of: chỉ dùng trans_date <= as_of_date, loại k_symbol = 'UVER'
DROP TABLE IF EXISTS clean.asof_features;
GO
WITH f AS (
  SELECT g.loan_id, g.account_id, g.k AS loan_age_k, g.as_of_date, YEAR(g.loan_date) AS loan_year,
         g.is_bad, g.event_k, g.months_to_event, g.is_pre_event, g.label_ambiguous,
         l.amount AS loan_amount, l.duration AS loan_duration, l.payments AS loan_payments,
         DATEDIFF(month, a.open_date, l.loan_date) AS acct_age_at_loan_m,
         h.hist_n_trans, h.hist_bal_min, h.hist_bal_avg, h.hist_bal_max, h.hist_bal_std,
         h.hist_neg_rows, h.hist_penalty_cnt,
         CAST(1.0 * h.hist_neg_rows / NULLIF(h.hist_n_trans, 0) AS decimal(9,4)) AS hist_neg_share,
         CAST(h.hist_credit_sum / mo.months_obs AS decimal(14,2)) AS hist_credit_avg_m,
         CAST(h.hist_debit_sum / mo.months_obs AS decimal(14,2)) AS hist_debit_avg_m,
         m.lm_n_trans, m.lm_credit_sum, m.lm_debit_sum, m.lm_bal_min
  FROM clean.asof_grid g
  JOIN clean.loan l ON l.loan_id = g.loan_id
  JOIN clean.account a ON a.account_id = g.account_id
  OUTER APPLY (
    SELECT COUNT(*) AS hist_n_trans, MIN(t.balance) AS hist_bal_min, AVG(t.balance) AS hist_bal_avg,
           MAX(t.balance) AS hist_bal_max, STDEV(t.balance) AS hist_bal_std,
           SUM(CASE WHEN t.balance < 0 THEN 1 ELSE 0 END) AS hist_neg_rows,
           SUM(CASE WHEN t.k_symbol = 'SANKC. UROK' THEN 1 ELSE 0 END) AS hist_penalty_cnt,
           SUM(CASE WHEN t.[type] = 'PRIJEM' THEN t.amount ELSE 0 END) AS hist_credit_sum,
           SUM(CASE WHEN t.[type] <> 'PRIJEM' THEN t.amount ELSE 0 END) AS hist_debit_sum,
           MIN(t.trans_date) AS first_trans_date
    FROM clean.trans t
    WHERE t.account_id = g.account_id AND t.trans_date <= g.as_of_date AND t.k_symbol <> 'UVER') h
  CROSS APPLY (SELECT CASE WHEN DATEDIFF(month, h.first_trans_date, g.as_of_date) + 1 < 1 THEN 1
                           ELSE DATEDIFF(month, h.first_trans_date, g.as_of_date) + 1 END AS months_obs) mo
  OUTER APPLY (
    -- tháng dương lịch ngay trước tháng của as_of_date (luôn nằm trước as_of_date)
    SELECT COUNT(*) AS lm_n_trans,
           ISNULL(SUM(CASE WHEN t.[type] = 'PRIJEM' THEN t.amount ELSE 0 END), 0) AS lm_credit_sum,
           ISNULL(SUM(CASE WHEN t.[type] <> 'PRIJEM' THEN t.amount ELSE 0 END), 0) AS lm_debit_sum,
           MIN(t.balance) AS lm_bal_min
    FROM clean.trans t
    WHERE t.account_id = g.account_id AND t.k_symbol <> 'UVER'
      AND t.trans_date >= DATEADD(month, -1, DATEFROMPARTS(YEAR(g.as_of_date), MONTH(g.as_of_date), 1))
      AND t.trans_date <  DATEFROMPARTS(YEAR(g.as_of_date), MONTH(g.as_of_date), 1)) m)
SELECT f.*,
       CAST(f.loan_payments / NULLIF(f.hist_credit_avg_m, 0) AS decimal(14,4)) AS loan_burden,
       CAST(f.lm_credit_sum / NULLIF(f.hist_credit_avg_m, 0) AS decimal(14,4)) AS lm_credit_ratio,
       CAST(f.lm_debit_sum / NULLIF(f.hist_debit_avg_m, 0) AS decimal(14,4)) AS lm_debit_ratio
INTO clean.asof_features FROM f;
GO
CREATE CLUSTERED INDEX ix_asof_features ON clean.asof_features (loan_id, loan_age_k);
GO
-- (1) Kiểm tra kích thước và giá trị thiếu
SELECT COUNT(*) AS rows_, (SELECT COUNT(*) FROM clean.asof_grid) AS grid_rows,
       SUM(CASE WHEN hist_n_trans = 0 THEN 1 ELSE 0 END) AS no_history_rows,
       SUM(CASE WHEN hist_credit_avg_m IS NULL OR hist_credit_avg_m = 0 THEN 1 ELSE 0 END) AS zero_credit_rows,
       SUM(CASE WHEN lm_n_trans = 0 THEN 1 ELSE 0 END) AS empty_last_month_rows,
       SUM(CASE WHEN loan_burden IS NULL THEN 1 ELSE 0 END) AS null_burden_rows
FROM clean.asof_features;
GO
-- (2) Kiểm tra hợp lý (chỉ năm giải ngân <= 1995, tức chỉ nhìn dữ liệu train, tránh nhìn trước tập test)
SELECT CASE WHEN is_bad = 1 THEN 'bad_with_event' ELSE 'good' END AS grp,
       COUNT(*) AS rows_, COUNT(DISTINCT loan_id) AS loans,
       CAST(AVG(hist_bal_min) AS decimal(12,0)) AS avg_hist_bal_min,
       CAST(AVG(hist_neg_share) AS decimal(9,4)) AS avg_neg_share,
       CAST(AVG(loan_burden) AS decimal(9,3)) AS avg_burden,
       CAST(AVG(hist_credit_avg_m) AS decimal(12,0)) AS avg_credit_per_month,
       CAST(AVG(lm_credit_ratio) AS decimal(9,3)) AS avg_lm_credit_ratio
FROM clean.asof_features
WHERE loan_year <= 1995 AND is_pre_event = 1 AND label_ambiguous = 0
GROUP BY CASE WHEN is_bad = 1 THEN 'bad_with_event' ELSE 'good' END;
GO
