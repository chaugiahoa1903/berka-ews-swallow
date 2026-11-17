-- sql/07_default_rule_check.sql - kiểm quy tắc "trả thiếu kỳ" làm mốc vỡ nợ đại diện
WITH n AS (SELECT TOP (60) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS k FROM sys.all_objects),
g AS (
  SELECT l.loan_id, l.status, n.k,
         (SELECT COUNT(*) FROM clean.trans t
          WHERE t.account_id = l.account_id AND t.k_symbol = 'UVER'
            AND t.trans_date > l.loan_date AND t.trans_date <= DATEADD(month, n.k, l.loan_date)) AS paid
  FROM clean.loan l
  JOIN n ON n.k <= l.duration AND DATEADD(month, n.k, l.loan_date) <= '1998-12-31'),
m AS (
  SELECT loan_id, status, MAX(k - paid) AS max_short_nograce, MAX(k - 1 - paid) AS max_short_grace1
  FROM g GROUP BY loan_id, status)
SELECT status, COUNT(*) AS loans,
       SUM(CASE WHEN max_short_nograce >= 1 THEN 1 ELSE 0 END) AS short1_nograce,
       SUM(CASE WHEN max_short_nograce >= 2 THEN 1 ELSE 0 END) AS short2_nograce,
       SUM(CASE WHEN max_short_grace1 >= 1 THEN 1 ELSE 0 END) AS short1_grace1,
       SUM(CASE WHEN max_short_grace1 >= 2 THEN 1 ELSE 0 END) AS short2_grace1
FROM m GROUP BY status ORDER BY status;
GO
