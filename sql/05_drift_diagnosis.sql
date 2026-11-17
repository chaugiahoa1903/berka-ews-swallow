-- sql/05_drift_diagnosis.sql - chẩn đoán vì sao cộng dồn không khớp balance
-- A) tỷ lệ khớp theo thứ tự ngày của tài khoản
SELECT CASE WHEN day_no <= 3 THEN '1-3' WHEN day_no <= 10 THEN '4-10' WHEN day_no <= 50 THEN '11-50'
            WHEN day_no <= 200 THEN '51-200' ELSE '201+' END AS day_bucket,
       COUNT(*) AS account_days,
       CAST(100.0 * SUM(m) / COUNT(*) AS decimal(5,2)) AS pct_match
FROM (SELECT d.*, ROW_NUMBER() OVER (PARTITION BY d.account_id ORDER BY d.trans_date) AS day_no,
             CASE WHEN EXISTS (SELECT 1 FROM clean.trans t WHERE t.account_id = d.account_id
                               AND t.trans_date = d.trans_date AND t.balance = d.eod_balance)
                  THEN 1 ELSE 0 END AS m
      FROM clean.daily_balance d) x
GROUP BY CASE WHEN day_no <= 3 THEN '1-3' WHEN day_no <= 10 THEN '4-10' WHEN day_no <= 50 THEN '11-50'
              WHEN day_no <= 200 THEN '51-200' ELSE '201+' END
ORDER BY MIN(day_no);
GO
-- B) cặp ngày liền kề không nhiễu: nhóm nào lệch, lệch bao nhiêu (gap = delta - amount có dấu)
WITH a AS (
  SELECT account_id, trans_date, trans_id, [type], operation, k_symbol, amount, balance,
         COUNT(*) OVER (PARTITION BY account_id, trans_date) AS n_same_day
  FROM clean.trans),
b AS (
  SELECT *, LAG(n_same_day) OVER (PARTITION BY account_id ORDER BY trans_date, trans_id) AS n_prev_day,
         balance - LAG(balance) OVER (PARTITION BY account_id ORDER BY trans_date, trans_id) AS delta
  FROM a),
c AS (
  SELECT [type], ISNULL(operation, '<NULL>') AS operation, k_symbol, amount,
         delta - CASE WHEN [type] = 'PRIJEM' THEN amount ELSE -amount END AS gap
  FROM b WHERE n_same_day = 1 AND n_prev_day = 1 AND delta IS NOT NULL)
SELECT [type], operation, k_symbol, COUNT(*) AS n,
       SUM(CASE WHEN gap <> 0 THEN 1 ELSE 0 END) AS n_mismatch,
       CAST(100.0 * SUM(CASE WHEN gap <> 0 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS pct_mismatch,
       CAST(AVG(CASE WHEN gap <> 0 THEN gap END) AS decimal(12,2)) AS avg_gap,
       MIN(gap) AS min_gap, MAX(gap) AS max_gap,
       CAST(AVG(CASE WHEN gap <> 0 AND amount <> 0 THEN gap / amount END) AS decimal(8,4)) AS avg_gap_over_amount
FROM c GROUP BY [type], operation, k_symbol
HAVING SUM(CASE WHEN gap <> 0 THEN 1 ELSE 0 END) > 0
ORDER BY n_mismatch DESC;
GO
