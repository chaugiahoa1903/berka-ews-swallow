USE Swallow;
GO
-- A) Cac khoan vay co chu tai khoan < 18 tuoi: phan bo theo nam giai ngan (chi dem, khong xem ket qua)
SELECT YEAR(l.loan_date) AS loan_year,
       COUNT(*) AS n_loans,
       SUM(CASE WHEN d.age_at_loan_y < 18 THEN 1 ELSE 0 END) AS n_under18
FROM clean.loan l
JOIN clean.loan_demographics d ON d.loan_id = l.loan_id
GROUP BY YEAR(l.loan_date) ORDER BY loan_year;
GO
-- B) Hien tuong nay co pho bien tren TOAN BO 4500 tai khoan khong? (tuoi chu tai khoan tai ngay mo tai khoan)
SELECT COUNT(*) AS n_accounts,
       SUM(CASE WHEN DATEDIFF(MONTH, c.birth_date, a.open_date) / 12.0 < 18 THEN 1 ELSE 0 END) AS n_owner_under18_at_open,
       CAST(100.0 * SUM(CASE WHEN DATEDIFF(MONTH, c.birth_date, a.open_date) / 12.0 < 18 THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS pct
FROM clean.account a
JOIN clean.disp d   ON d.account_id = a.account_id AND d.disp_type = 'OWNER'
JOIN clean.client c ON c.client_id = d.client_id;
GO
-- C (da sua) Voi cac khoan do: co DISPONENT khong, DISPONENT lon tuoi nhat co >= 18 tuoi tai ngay vay khong
-- Sua loi 8124: tinh MIN(birth_date) theo tai khoan o truy van con rieng, tinh tuoi o ben ngoai
SELECT COUNT(*) AS n_under18_loans,
       SUM(CASE WHEN dis.oldest_birth IS NOT NULL THEN 1 ELSE 0 END) AS n_with_disponent,
       SUM(CASE WHEN dis.oldest_birth IS NOT NULL
                 AND DATEDIFF(MONTH, dis.oldest_birth, l.loan_date) / 12.0 >= 18 THEN 1 ELSE 0 END) AS n_disponent_adult
FROM clean.loan l
JOIN clean.loan_demographics dm ON dm.loan_id = l.loan_id AND dm.age_at_loan_y < 18
LEFT JOIN (
    SELECT d2.account_id, MIN(c2.birth_date) AS oldest_birth
    FROM clean.disp d2
    JOIN clean.client c2 ON c2.client_id = d2.client_id
    WHERE d2.disp_type = 'DISPONENT'
    GROUP BY d2.account_id
) dis ON dis.account_id = l.account_id;
GO