-- sql/21_alert_kpi_monthly.sql
-- Bang KPI giam sat hang thang, tinh CHI tu mart.alerts (khong dung nhan, khong dung ket qua that).
-- Chay lai duoc: xoa bang cu roi tao lai. Dinh nghia chi so: reports/metrics_dictionary.md
-- "moi" = khoan vay lan dau co alert = 1 (khop dinh nghia cua src/alert_report.py)

IF OBJECT_ID('mart.alert_kpi_monthly', 'U') IS NOT NULL DROP TABLE mart.alert_kpi_monthly;

WITH first_alert AS (
    SELECT loan_id, MIN(replay_month) AS first_alert_month
    FROM mart.alerts
    WHERE alert = 1
    GROUP BY loan_id
),
monthly AS (
    SELECT
        a.replay_month,
        COUNT(*) AS n_scored,
        SUM(CASE WHEN a.alert = 1 THEN 1 ELSE 0 END) AS n_alerts,
        SUM(CASE WHEN a.alert = 1 AND a.replay_month = f.first_alert_month THEN 1 ELSE 0 END) AS n_new,
        SUM(CASE WHEN a.alert = 1 AND a.replay_month > f.first_alert_month THEN 1 ELSE 0 END) AS n_continuing,
        SUM(CASE WHEN a.ever_neg = 1 THEN 1 ELSE 0 END) AS n_ever_neg,
        SUM(CASE WHEN a.ever_neg = 1 AND a.alert = 0 THEN 1 ELSE 0 END) AS n_ever_neg_not_alerted,
        AVG(CAST(a.score AS float)) AS mean_score,
        MAX(CAST(a.score AS float)) AS max_score,
        MAX(CAST(a.threshold AS float)) AS threshold,
        COUNT(DISTINCT a.model_file) AS n_model_files
    FROM mart.alerts a
    LEFT JOIN first_alert f ON f.loan_id = a.loan_id
    GROUP BY a.replay_month
)
SELECT
    replay_month,
    n_scored,
    n_alerts,
    CAST(n_alerts AS float) / NULLIF(n_scored, 0) AS alert_rate,
    n_new,
    n_continuing,
    SUM(n_new) OVER (ORDER BY replay_month ROWS UNBOUNDED PRECEDING) AS cum_loans_alerted,
    n_ever_neg,
    n_ever_neg_not_alerted,
    mean_score,
    max_score,
    threshold,
    n_model_files,
    SYSDATETIME() AS computed_at
INTO mart.alert_kpi_monthly
FROM monthly;

-- Doi chieu (ket qua mong doi ghi o cot cuoi: sum_n_new = loans_ever_alerted, months_in_kpi = months_in_alerts, alerts_unexplained = 0)
SELECT
    (SELECT SUM(n_new) FROM mart.alert_kpi_monthly) AS sum_n_new,
    (SELECT COUNT(DISTINCT loan_id) FROM mart.alerts WHERE alert = 1) AS loans_ever_alerted,
    (SELECT COUNT(*) FROM mart.alert_kpi_monthly) AS months_in_kpi,
    (SELECT COUNT(DISTINCT replay_month) FROM mart.alerts) AS months_in_alerts,
    (SELECT SUM(n_alerts) - SUM(n_new) - SUM(n_continuing) FROM mart.alert_kpi_monthly) AS alerts_unexplained,
    (SELECT MAX(n_model_files) FROM mart.alert_kpi_monthly) AS max_model_files_per_month;
