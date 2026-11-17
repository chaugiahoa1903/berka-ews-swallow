-- sql/08_event_and_grid.sql - mốc vỡ nợ đại diện (thiếu >= 2 kỳ UVER) và khung as-of
-- LƯU Ý: loan_month_payment dùng UVER chỉ để định nghĩa nhãn/sự kiện, KHÔNG dùng làm đặc trưng.
DROP TABLE IF EXISTS clean.loan_month_payment;
GO
WITH n AS (SELECT TOP (60) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS k FROM sys.all_objects)
SELECT l.loan_id, n.k, DATEADD(month, n.k, l.loan_date) AS as_of_date,
       (SELECT COUNT(*) FROM clean.trans t
        WHERE t.account_id = l.account_id AND t.k_symbol = 'UVER'
          AND t.trans_date >= l.loan_date AND t.trans_date <= DATEADD(month, n.k, l.loan_date)) AS paid_cum
INTO clean.loan_month_payment
FROM clean.loan l
JOIN n ON n.k <= l.duration AND DATEADD(month, n.k, l.loan_date) <= '1998-12-31';
GO
CREATE CLUSTERED INDEX ix_lmp ON clean.loan_month_payment (loan_id, k);
GO
DROP TABLE IF EXISTS clean.loan_event;
GO
SELECT l.loan_id, l.account_id, l.loan_date, l.end_date, l.duration, l.status, l.is_bad, l.is_censored,
       CASE WHEN EXISTS (SELECT 1 FROM clean.loan_month_payment m WHERE m.loan_id = l.loan_id)
            THEN 1 ELSE 0 END AS is_observable,
       e.event_k,
       DATEADD(month, e.event_k, l.loan_date) AS event_date
INTO clean.loan_event
FROM clean.loan l
OUTER APPLY (SELECT MIN(m.k) AS event_k FROM clean.loan_month_payment m
             WHERE m.loan_id = l.loan_id AND m.k - m.paid_cum >= 2) e;
GO
DROP TABLE IF EXISTS clean.asof_grid;
GO
SELECT m.loan_id, e.account_id, e.loan_date, m.k, m.as_of_date,
       e.status, e.is_bad, e.duration, e.event_k,
       CASE WHEN e.event_k IS NOT NULL THEN e.event_k - m.k END AS months_to_event,
       CASE WHEN e.event_k IS NULL OR m.k < e.event_k THEN 1 ELSE 0 END AS is_pre_event,
       CASE WHEN e.is_bad = 1 AND e.event_k IS NULL THEN 1 ELSE 0 END AS label_ambiguous
INTO clean.asof_grid
FROM clean.loan_month_payment m
JOIN clean.loan_event e ON e.loan_id = m.loan_id;
GO
CREATE CLUSTERED INDEX ix_asof_grid ON clean.asof_grid (account_id, as_of_date);
GO
-- (1) Tóm tắt mốc vỡ nợ theo status
SELECT status, COUNT(*) AS loans, SUM(is_observable) AS observable,
       SUM(CASE WHEN event_k IS NOT NULL THEN 1 ELSE 0 END) AS with_event,
       CAST(AVG(1.0 * event_k) AS decimal(6,2)) AS avg_event_k, MIN(event_k) AS min_event_k, MAX(event_k) AS max_event_k,
       CAST(AVG(CASE WHEN event_k IS NOT NULL THEN 1.0 * duration END) AS decimal(6,2)) AS avg_duration,
       SUM(CASE WHEN event_k <= 3 THEN 1 ELSE 0 END) AS event_within_3m
FROM clean.loan_event GROUP BY status ORDER BY status;
GO
-- (2) Kích thước khung as-of
SELECT is_bad, label_ambiguous, is_pre_event, COUNT(*) AS rows_, COUNT(DISTINCT loan_id) AS loans
FROM clean.asof_grid GROUP BY is_bad, label_ambiguous, is_pre_event ORDER BY is_bad, label_ambiguous, is_pre_event;
GO

