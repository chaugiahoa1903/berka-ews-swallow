-- sql/02_checks.sql - kiểm chứng lớp clean và hai nghi vấn về trans
-- (a) Số dòng khớp staging, chuyển kiểu hỏng (kỳ vọng bad_cast = 0)
SELECT 'trans' AS tbl, COUNT(*) AS rows_clean, (SELECT COUNT(*) FROM stg.trans) AS rows_stg,
       SUM(CASE WHEN trans_date IS NULL OR amount IS NULL OR balance IS NULL THEN 1 ELSE 0 END) AS bad_cast
FROM clean.trans
UNION ALL
SELECT 'loan', COUNT(*), (SELECT COUNT(*) FROM stg.loan),
       SUM(CASE WHEN loan_date IS NULL OR amount IS NULL OR duration IS NULL OR payments IS NULL THEN 1 ELSE 0 END)
FROM clean.loan
UNION ALL
SELECT 'account', COUNT(*), (SELECT COUNT(*) FROM stg.account),
       SUM(CASE WHEN open_date IS NULL OR district_id IS NULL THEN 1 ELSE 0 END)
FROM clean.account
UNION ALL
SELECT 'client', COUNT(*), (SELECT COUNT(*) FROM stg.client),
       SUM(CASE WHEN birth_date IS NULL OR gender IS NULL THEN 1 ELSE 0 END)
FROM clean.client;
GO
-- (b) Nhãn khoản vay: kỳ vọng is_bad = 1 có 76 khoản, is_finished = 1 có 234 khoản
SELECT status, is_finished, is_censored, is_bad, COUNT(*) AS n
FROM clean.loan GROUP BY status, is_finished, is_censored, is_bad ORDER BY status;
GO
-- (c) operation NULL có đúng là nhóm k_symbol = UROK không
SELECT CASE WHEN operation IS NULL THEN 'operation NULL' ELSE 'operation có giá trị' END AS operation_state,
       CASE WHEN k_symbol = 'UROK' THEN 'UROK' ELSE 'khác' END AS k_symbol_state,
       COUNT(*) AS n
FROM clean.trans GROUP BY CASE WHEN operation IS NULL THEN 'operation NULL' ELSE 'operation có giá trị' END,
                          CASE WHEN k_symbol = 'UROK' THEN 'UROK' ELSE 'khác' END;
GO
-- (d) Hướng dòng tiền: so dấu chênh lệch balance với type/operation
WITH t AS (
  SELECT [type], operation, amount,
         balance - LAG(balance) OVER (PARTITION BY account_id ORDER BY trans_date, trans_id) AS delta
  FROM clean.trans)
SELECT [type], ISNULL(operation, '<NULL>') AS operation, COUNT(*) AS n,
       SUM(CASE WHEN delta > 0 THEN 1 ELSE 0 END) AS balance_up,
       SUM(CASE WHEN delta < 0 THEN 1 ELSE 0 END) AS balance_down,
       SUM(CASE WHEN ABS(delta) = amount THEN 1 ELSE 0 END) AS delta_equals_amount
FROM t WHERE delta IS NOT NULL
GROUP BY [type], operation ORDER BY [type], operation;
GO
