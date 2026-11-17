-- sql/06_payment_check.sql - chuỗi trả góp (UVER) có phân biệt được khoản vay tốt/xấu không
WITH p AS (
  SELECT l.loan_id, l.status, l.is_censored,
         (SELECT COUNT(*) FROM clean.trans t
          WHERE t.account_id = l.account_id AND t.k_symbol = 'UVER' AND t.trans_date > l.loan_date) AS n_pay,
         CASE WHEN l.is_censored = 1 THEN DATEDIFF(month, l.loan_date, '1998-12-31') ELSE l.duration END AS expected
  FROM clean.loan l)
SELECT status, COUNT(*) AS loans,
       CAST(AVG(1.0 * n_pay) AS decimal(8,2)) AS avg_payments,
       CAST(AVG(1.0 * expected) AS decimal(8,2)) AS avg_expected,
       SUM(CASE WHEN n_pay = 0 THEN 1 ELSE 0 END) AS zero_payments,
       SUM(CASE WHEN n_pay >= expected THEN 1 ELSE 0 END) AS paid_all_due
FROM p GROUP BY status ORDER BY status;
GO
