-- sql/11_rule_robustness.sql - hai kiểm tra độ vững của quy tắc "thiếu >= 2 kỳ"
-- (1) Bảng đánh đổi theo nhóm năm giải ngân: quy tắc chọn trên 1993-1995 có giống toàn mẫu không
WITH m AS (
  SELECT loan_id, MAX(k - paid_cum) AS max_short FROM clean.loan_month_payment GROUP BY loan_id)
SELECT CASE WHEN l.loan_date < '1996-01-01' THEN '1993-1995'
            WHEN l.loan_date < '1998-01-01' THEN '1996-1997' ELSE '1998' END AS vintage,
       SUM(CASE WHEN l.is_bad = 1 THEN 1 ELSE 0 END) AS bad,
       SUM(CASE WHEN l.is_bad = 0 THEN 1 ELSE 0 END) AS good,
       CAST(100.0 * SUM(CASE WHEN l.is_bad = 1 AND m.max_short >= 1 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN l.is_bad = 1 THEN 1 ELSE 0 END), 0) AS decimal(5,1)) AS det_ge1_pct,
       CAST(100.0 * SUM(CASE WHEN l.is_bad = 1 AND m.max_short >= 2 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN l.is_bad = 1 THEN 1 ELSE 0 END), 0) AS decimal(5,1)) AS det_ge2_pct,
       CAST(100.0 * SUM(CASE WHEN l.is_bad = 1 AND m.max_short >= 3 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN l.is_bad = 1 THEN 1 ELSE 0 END), 0) AS decimal(5,1)) AS det_ge3_pct,
       CAST(100.0 * SUM(CASE WHEN l.is_bad = 0 AND m.max_short >= 1 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN l.is_bad = 0 THEN 1 ELSE 0 END), 0) AS decimal(5,1)) AS fp_ge1_pct,
       CAST(100.0 * SUM(CASE WHEN l.is_bad = 0 AND m.max_short >= 2 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN l.is_bad = 0 THEN 1 ELSE 0 END), 0) AS decimal(5,1)) AS fp_ge2_pct,
       CAST(100.0 * SUM(CASE WHEN l.is_bad = 0 AND m.max_short >= 3 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN l.is_bad = 0 THEN 1 ELSE 0 END), 0) AS decimal(5,1)) AS fp_ge3_pct
FROM clean.loan l JOIN m ON m.loan_id = l.loan_id
GROUP BY CASE WHEN l.loan_date < '1996-01-01' THEN '1993-1995'
              WHEN l.loan_date < '1998-01-01' THEN '1996-1997' ELSE '1998' END
ORDER BY vintage;
GO
-- (2) Số tiền mỗi lần trả UVER so với kỳ trả quy định của khoản vay (cho phép lệch +-1 vì làm tròn)
SELECT l.status, COUNT(*) AS uver_rows,
       SUM(CASE WHEN t.amount = l.payments THEN 1 ELSE 0 END) AS equal_payments,
       SUM(CASE WHEN ABS(t.amount - l.payments) <= 1 THEN 1 ELSE 0 END) AS within_1,
       SUM(CASE WHEN t.amount < l.payments - 1 THEN 1 ELSE 0 END) AS below_payments,
       SUM(CASE WHEN t.amount > l.payments + 1 THEN 1 ELSE 0 END) AS above_payments
FROM clean.loan l
JOIN clean.trans t ON t.account_id = l.account_id AND t.k_symbol = 'UVER' AND t.trans_date > l.loan_date
GROUP BY l.status ORDER BY l.status;
GO
