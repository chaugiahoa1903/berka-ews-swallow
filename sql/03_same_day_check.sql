-- sql/03_same_day_check.sql - phép thử giả thuyết "lệch do thứ tự giao dịch trong cùng ngày"
WITH a AS (
  SELECT account_id, trans_date, trans_id, [type], operation, amount, balance,
         COUNT(*) OVER (PARTITION BY account_id, trans_date) AS n_same_day
  FROM clean.trans),
b AS (
  SELECT *,
         LAG(n_same_day) OVER (PARTITION BY account_id ORDER BY trans_date, trans_id) AS n_prev_day,
         balance - LAG(balance) OVER (PARTITION BY account_id ORDER BY trans_date, trans_id) AS delta
  FROM a)
SELECT CASE WHEN n_same_day = 1 AND n_prev_day = 1 THEN '1 - cả hai ngày chỉ 1 giao dịch'
            ELSE '2 - còn lại' END AS grp,
       [type], ISNULL(operation, '<NULL>') AS operation, COUNT(*) AS n,
       CAST(100.0 * SUM(CASE WHEN ABS(delta) = amount THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS pct_equal,
       CAST(100.0 * SUM(CASE WHEN delta > 0 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS pct_balance_up
FROM b WHERE delta IS NOT NULL
GROUP BY CASE WHEN n_same_day = 1 AND n_prev_day = 1 THEN '1 - cả hai ngày chỉ 1 giao dịch'
              ELSE '2 - còn lại' END, [type], operation
ORDER BY grp, [type], operation;
GO
