-- sql/10_event_timing.sql - phân phối thời điểm vỡ nợ đại diện, để lấy các mốc từ dữ liệu
-- (1) phân phối và phần trăm tích lũy theo tháng sau giải ngân (60 khoản xấu có mốc)
SELECT event_k, COUNT(*) AS events,
       SUM(COUNT(*)) OVER (ORDER BY event_k) AS cum_events,
       CAST(100.0 * SUM(COUNT(*)) OVER (ORDER BY event_k) / SUM(COUNT(*)) OVER () AS decimal(5,1)) AS cum_pct
FROM clean.loan_event WHERE is_bad = 1 AND event_k IS NOT NULL
GROUP BY event_k ORDER BY event_k;
GO
-- (2) tứ phân vị
SELECT DISTINCT
       PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY event_k) OVER () AS q1,
       PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY event_k) OVER () AS median,
       PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY event_k) OVER () AS q3
FROM clean.loan_event WHERE is_bad = 1 AND event_k IS NOT NULL;
GO
-- (3) kiểm tra TOP (60) ở bước 8 có cắt cụt kỳ hạn nào không (cần max_duration <= 60)
SELECT MIN(duration) AS min_duration, MAX(duration) AS max_duration FROM clean.loan;
GO
