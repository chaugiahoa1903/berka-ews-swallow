USE Swallow;
GO
-- 1) Nhat ky chay: lan chay moi nhat cua tung thang
WITH r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY replay_month ORDER BY run_id DESC) AS rn FROM mart.run_log)
SELECT replay_month, n_scored, n_alerts, dq_ok, dq_message FROM r WHERE rn = 1 ORDER BY replay_month;
GO
-- 2) Khoan bi canh bao it nhat 1 lan trong replay, chia theo nhom (doi chieu voi test 1997: ky vong duong = 15, am = 0)
WITH lf AS (
    SELECT loan_id,
           MAX(CASE WHEN event_k IS NOT NULL THEN 1 ELSE 0 END) AS has_event,
           MAX(CAST(label_ambiguous AS INT)) AS amb
    FROM clean.asof_features GROUP BY loan_id
), fa AS (
    SELECT loan_id FROM mart.alerts WHERE alert = 1 GROUP BY loan_id
)
SELECT grp, COUNT(*) AS n_loans_alerted
FROM (SELECT CASE WHEN lf.amb = 1 THEN '3_mo_ho (xau, khong moc)'
                  WHEN lf.has_event = 1 THEN '1_duong (co moc)'
                  ELSE '2_am (khong moc)' END AS grp
      FROM fa JOIN lf ON lf.loan_id = fa.loan_id) x
GROUP BY grp ORDER BY grp;
GO
-- 3) Lead time cua cac khoan duong duoc canh bao (ky vong median = 1.0)
WITH lf AS (
    SELECT loan_id, MAX(event_k) AS event_k
    FROM clean.asof_features GROUP BY loan_id
), fa AS (
    SELECT loan_id, MIN(loan_age_k) AS first_alert_k FROM mart.alerts WHERE alert = 1 GROUP BY loan_id
), d AS (
    SELECT CAST(lf.event_k - fa.first_alert_k AS FLOAT) AS lead
    FROM fa JOIN lf ON lf.loan_id = fa.loan_id WHERE lf.event_k IS NOT NULL
)
SELECT DISTINCT COUNT(*) OVER () AS n_pos_alerted,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lead) OVER () AS lead_median,
       MIN(lead) OVER () AS lead_min, MAX(lead) OVER () AS lead_max
FROM d;
GO
