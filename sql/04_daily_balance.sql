-- sql/04_daily_balance.sql - số dư cuối ngày tính bằng cộng dồn amount có dấu (không phụ thuộc thứ tự trong ngày)
DROP TABLE IF EXISTS clean.daily_balance;
GO
WITH d AS (
  SELECT account_id, trans_date, COUNT(*) AS n_trans,
         SUM(CASE WHEN [type] = 'PRIJEM' THEN amount ELSE -amount END) AS net_amount,
         MIN(balance) AS min_row_balance, MAX(balance) AS max_row_balance
  FROM clean.trans GROUP BY account_id, trans_date)
SELECT account_id, trans_date, n_trans, net_amount, min_row_balance, max_row_balance,
       SUM(net_amount) OVER (PARTITION BY account_id ORDER BY trans_date
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS eod_balance
INTO clean.daily_balance FROM d;
GO
CREATE CLUSTERED INDEX ix_daily_balance ON clean.daily_balance (account_id, trans_date);
GO
-- Kiểm chứng: eod_balance phải trùng balance của ít nhất một dòng trong ngày, và nằm trong [min, max] của các dòng đó
SELECT grp, COUNT(*) AS account_days,
       SUM(matches_a_row) AS eod_matches_a_row,
       CAST(100.0 * SUM(matches_a_row) / COUNT(*) AS decimal(5,2)) AS pct_match,
       SUM(within_min_max) AS eod_within_min_max
FROM (
  SELECT CASE WHEN d.n_trans = 1 THEN 'single' ELSE 'multi' END AS grp,
         CASE WHEN EXISTS (SELECT 1 FROM clean.trans t
                           WHERE t.account_id = d.account_id AND t.trans_date = d.trans_date
                             AND t.balance = d.eod_balance) THEN 1 ELSE 0 END AS matches_a_row,
         CASE WHEN d.eod_balance BETWEEN d.min_row_balance AND d.max_row_balance THEN 1 ELSE 0 END AS within_min_max
  FROM clean.daily_balance d) x
GROUP BY grp ORDER BY grp;
GO
-- Xem trước bẫy leakage: bao nhiêu tài khoản từng có số dư cuối ngày âm
SELECT COUNT(DISTINCT account_id) AS accounts_total,
       COUNT(DISTINCT CASE WHEN eod_balance < 0 THEN account_id END) AS accounts_ever_negative,
       MIN(eod_balance) AS min_eod_balance
FROM clean.daily_balance;
GO
