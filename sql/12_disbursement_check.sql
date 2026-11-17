-- sql/12_disbursement_check.sql - giao dịch ngày giải ngân và 22 dòng UVER chưa gắn được vào kỳ trả
-- (1) Trong ngày giải ngân, tài khoản có những giao dịch gì; có dòng nào đúng bằng số tiền vay không
SELECT t.[type], ISNULL(t.operation, '<NULL>') AS operation, t.k_symbol, COUNT(*) AS n,
       SUM(CASE WHEN t.amount = l.amount THEN 1 ELSE 0 END) AS amount_equals_loan_amount,
       CAST(AVG(t.amount) AS decimal(12,0)) AS avg_amount
FROM clean.loan l
JOIN clean.trans t ON t.account_id = l.account_id AND t.trans_date = l.loan_date
GROUP BY t.[type], t.operation, t.k_symbol ORDER BY n DESC;
GO
-- (2) Các dòng UVER không nằm sau ngày giải ngân của khoản vay nào
SELECT CASE WHEN l.loan_id IS NULL THEN 'account_has_no_loan'
            WHEN t.trans_date = l.loan_date THEN 'on_loan_date' ELSE 'before_loan_date' END AS where_,
       t.[type], COUNT(*) AS n
FROM clean.trans t
LEFT JOIN clean.loan l ON l.account_id = t.account_id
WHERE t.k_symbol = 'UVER' AND (l.loan_id IS NULL OR t.trans_date <= l.loan_date)
GROUP BY CASE WHEN l.loan_id IS NULL THEN 'account_has_no_loan'
              WHEN t.trans_date = l.loan_date THEN 'on_loan_date' ELSE 'before_loan_date' END, t.[type];
GO
