-- sql/20: thang replay nao co canh bao moi (khoan vay lan dau co alert = 1)
WITH first_alert AS (
  SELECT loan_id, MIN(replay_month) AS first_month
  FROM mart.alerts WHERE alert = 1 GROUP BY loan_id)
SELECT first_month AS replay_month, COUNT(*) AS n_new
FROM first_alert GROUP BY first_month ORDER BY first_month;
GO
WITH first_alert AS (
  SELECT loan_id, MIN(replay_month) AS first_month
  FROM mart.alerts WHERE alert = 1 GROUP BY loan_id)
SELECT COUNT(DISTINCT first_month) AS months_with_new, COUNT(*) AS loans_ever_alerted,
       (SELECT COUNT(DISTINCT replay_month) FROM mart.alerts) AS months_in_table
FROM first_alert;
