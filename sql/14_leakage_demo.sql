-- sql/14_leakage_demo.sql - min(balance) < 0 tách khoản xấu/tốt thế nào khi bỏ qua thời gian so với đúng mốc as-of
WITH full_hist AS (
  SELECT e.loan_id, e.is_bad, MIN(t.balance) AS min_bal
  FROM clean.loan_event e JOIN clean.trans t ON t.account_id = e.account_id
  WHERE e.is_observable = 1 GROUP BY e.loan_id, e.is_bad),
at_disb AS (
  SELECT e.loan_id, e.is_bad, MIN(t.balance) AS min_bal
  FROM clean.loan_event e
  LEFT JOIN clean.trans t ON t.account_id = e.account_id AND t.trans_date <= e.loan_date
  WHERE e.is_observable = 1 GROUP BY e.loan_id, e.is_bad),
at_k1 AS (
  SELECT loan_id, is_bad, hist_bal_min AS min_bal FROM clean.asof_features WHERE loan_age_k = 1)
SELECT 'A_full_history_ignoring_time' AS version_, CASE WHEN min_bal < 0 THEN 'min<0' ELSE 'min>=0' END AS grp,
       COUNT(*) AS loans, SUM(is_bad) AS bad, CAST(100.0 * SUM(is_bad) / COUNT(*) AS decimal(5,1)) AS bad_pct
FROM full_hist GROUP BY CASE WHEN min_bal < 0 THEN 'min<0' ELSE 'min>=0' END
UNION ALL
SELECT 'B_asof_at_disbursement', CASE WHEN min_bal IS NULL THEN 'no_history' WHEN min_bal < 0 THEN 'min<0' ELSE 'min>=0' END,
       COUNT(*), SUM(is_bad), CAST(100.0 * SUM(is_bad) / COUNT(*) AS decimal(5,1))
FROM at_disb GROUP BY CASE WHEN min_bal IS NULL THEN 'no_history' WHEN min_bal < 0 THEN 'min<0' ELSE 'min>=0' END
UNION ALL
SELECT 'C_asof_1_month_after', CASE WHEN min_bal IS NULL THEN 'no_history' WHEN min_bal < 0 THEN 'min<0' ELSE 'min>=0' END,
       COUNT(*), SUM(is_bad), CAST(100.0 * SUM(is_bad) / COUNT(*) AS decimal(5,1))
FROM at_k1 GROUP BY CASE WHEN min_bal IS NULL THEN 'no_history' WHEN min_bal < 0 THEN 'min<0' ELSE 'min>=0' END
ORDER BY 1, 2;
GO
