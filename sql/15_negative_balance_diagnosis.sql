USE Swallow;
GO
-- Q1: ngay tu lan am dau tien (<= as_of k=1, bo UVER) den loan_date, chi khoan xau am tai k=1
-- duong = am TRUOC giai ngan; am = am SAU giai ngan
WITH neg AS (
    SELECT g.loan_id, g.loan_date,
           MIN(t.trans_date) AS first_neg
    FROM clean.asof_grid g
    JOIN clean.asof_features f ON f.loan_id = g.loan_id AND f.loan_age_k = 1
    JOIN clean.trans t ON t.account_id = g.account_id
         AND t.trans_date <= g.as_of_date AND t.k_symbol <> 'UVER' AND t.balance < 0
    WHERE g.k = 1 AND g.is_bad = 1 AND f.hist_bal_min < 0
    GROUP BY g.loan_id, g.loan_date
), d AS (
    SELECT loan_id, DATEDIFF(DAY, first_neg, loan_date) AS days_before_loan FROM neg
)
SELECT DISTINCT
    COUNT(*) OVER () AS n,
    MIN(days_before_loan) OVER () AS min_d,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY days_before_loan) OVER () AS q1,
    PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY days_before_loan) OVER () AS median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY days_before_loan) OVER () AS q3,
    MAX(days_before_loan) OVER () AS max_d
FROM d;
GO
-- Q2 (da sua): ty le tai khoan tung am theo nhom
-- Luu y: no_loan quan sat toi 1998-12-31, co vay chi quan sat toi loan_date -> khong cung cua so, doc than trong
WITH acc AS (
    SELECT a.account_id,
           CASE WHEN l.loan_id IS NULL THEN 'no_loan'
                WHEN l.is_bad = 1 THEN 'loan_bad' ELSE 'loan_good' END AS grp,
           l.loan_date
    FROM clean.account a
    LEFT JOIN clean.loan l ON l.account_id = a.account_id
), flag AS (
    SELECT acc.grp,
           CASE WHEN EXISTS (SELECT 1 FROM clean.trans t
                  WHERE t.account_id = acc.account_id AND t.balance < 0
                    AND t.k_symbol <> 'UVER'
                    AND (acc.loan_date IS NULL OR t.trans_date <= acc.loan_date))
                THEN 1 ELSE 0 END AS ever_neg
    FROM acc
)
SELECT grp, COUNT(*) AS n_accounts, SUM(ever_neg) AS n_ever_neg,
       CAST(100.0 * SUM(ever_neg) / COUNT(*) AS DECIMAL(5,1)) AS pct_ever_neg
FROM flag GROUP BY grp ORDER BY grp;
GO
-- Q3: tin hieu theo nam giai ngan tai k=1
SELECT loan_year,
       SUM(is_bad) AS bad,
       SUM(CASE WHEN is_bad = 1 AND hist_bal_min < 0 THEN 1 ELSE 0 END) AS bad_neg_k1,
       SUM(1 - is_bad) AS good,
       SUM(CASE WHEN is_bad = 0 AND hist_bal_min < 0 THEN 1 ELSE 0 END) AS good_neg_k1
FROM clean.asof_features
WHERE loan_age_k = 1
GROUP BY loan_year ORDER BY loan_year;
GO