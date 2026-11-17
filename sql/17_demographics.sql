USE Swallow;
GO
-- 1) Chuan hoa disp (ep kieu)
DROP TABLE IF EXISTS clean.disp;
SELECT CAST(disp_id AS INT)    AS disp_id,
       CAST(client_id AS INT)  AS client_id,
       CAST(account_id AS INT) AS account_id,
       UPPER(LTRIM(RTRIM([type]))) AS disp_type
INTO clean.disp
FROM stg.disp;
GO
-- 2) Kiem tra: so dong, phan bo type, so OWNER tren moi tai khoan
SELECT disp_type, COUNT(*) AS n, COUNT(DISTINCT account_id) AS n_accounts FROM clean.disp GROUP BY disp_type;
GO
SELECT n_owner, COUNT(*) AS n_accounts
FROM (SELECT a.account_id,
             SUM(CASE WHEN d.disp_type = 'OWNER' THEN 1 ELSE 0 END) AS n_owner
      FROM clean.account a
      LEFT JOIN clean.disp d ON d.account_id = a.account_id
      GROUP BY a.account_id) x
GROUP BY n_owner ORDER BY n_owner;
GO
-- 3) Bang nhan khau hoc theo khoan vay (OWNER cua tai khoan vay)
DROP TABLE IF EXISTS clean.loan_demographics;
SELECT l.loan_id,
       c.client_id,
       c.gender,
       c.birth_date,
       CAST(DATEDIFF(MONTH, c.birth_date, l.loan_date) / 12.0 AS DECIMAL(5,2)) AS age_at_loan_y
INTO clean.loan_demographics
FROM clean.loan l
JOIN clean.disp d   ON d.account_id = l.account_id AND d.disp_type = 'OWNER'
JOIN clean.client c ON c.client_id = d.client_id;
GO
-- 4) Kiem tra bang: so dong (ky vong 682 = 1 dong / khoan vay), trung loan_id, null, tuoi bat thuong
SELECT COUNT(*) AS n_rows, COUNT(DISTINCT loan_id) AS n_loans,
       SUM(CASE WHEN gender IS NULL OR birth_date IS NULL THEN 1 ELSE 0 END) AS n_null,
       SUM(CASE WHEN age_at_loan_y < 18 THEN 1 ELSE 0 END) AS n_age_lt18,
       MIN(age_at_loan_y) AS age_min, MAX(age_at_loan_y) AS age_max
FROM clean.loan_demographics;
GO
SELECT gender, COUNT(*) AS n FROM clean.loan_demographics GROUP BY gender;
GO
-- 5) Mo ta theo ket qua, CHI vintage <= 1995 (khong nhin truoc tap test)
SELECT d.gender, COUNT(*) AS n_loans, SUM(CAST(l.is_bad AS INT)) AS n_bad,
       CAST(100.0 * SUM(CAST(l.is_bad AS INT)) / COUNT(*) AS DECIMAL(5,1)) AS pct_bad
FROM clean.loan l JOIN clean.loan_demographics d ON d.loan_id = l.loan_id
WHERE YEAR(l.loan_date) <= 1995
GROUP BY d.gender ORDER BY d.gender;
GO
SELECT l.is_bad, COUNT(*) AS n_loans,
       CAST(AVG(d.age_at_loan_y) AS DECIMAL(5,1)) AS mean_age,
       CAST(STDEV(d.age_at_loan_y) AS DECIMAL(5,1)) AS sd_age
FROM clean.loan l JOIN clean.loan_demographics d ON d.loan_id = l.loan_id
WHERE YEAR(l.loan_date) <= 1995
GROUP BY l.is_bad ORDER BY l.is_bad;
GO