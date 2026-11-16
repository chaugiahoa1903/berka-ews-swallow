-- sql/01_clean.sql - lớp clean: ép kiểu, chuẩn hóa mã, nhãn khoản vay (Phương án 1)
IF SCHEMA_ID('clean') IS NULL EXEC('CREATE SCHEMA clean');
GO
DROP TABLE IF EXISTS clean.account;
SELECT CAST(TRY_CONVERT(decimal(18,0), account_id) AS int) AS account_id,
       CAST(TRY_CONVERT(decimal(18,0), district_id) AS int) AS district_id,
       frequency,
       TRY_CONVERT(date, [date]) AS open_date
INTO clean.account FROM stg.account;
GO
DROP TABLE IF EXISTS clean.client;
SELECT CAST(TRY_CONVERT(decimal(18,0), client_id) AS int) AS client_id,
       gender,
       TRY_CONVERT(date, birth_date) AS birth_date,
       CAST(TRY_CONVERT(decimal(18,0), district_id) AS int) AS district_id
INTO clean.client FROM stg.client;
GO
-- Nhãn: is_bad = B hoặc D (76 khoản); is_finished = A hoặc B; is_censored theo ngày, không theo status
DROP TABLE IF EXISTS clean.loan;
WITH b AS (
  SELECT CAST(TRY_CONVERT(decimal(18,0), loan_id) AS int) AS loan_id,
         CAST(TRY_CONVERT(decimal(18,0), account_id) AS int) AS account_id,
         TRY_CONVERT(date, [date]) AS loan_date,
         TRY_CONVERT(decimal(18,2), amount) AS amount,
         CAST(TRY_CONVERT(decimal(18,0), duration) AS int) AS duration,
         TRY_CONVERT(decimal(18,2), payments) AS payments,
         status
  FROM stg.loan)
SELECT b.*,
       DATEADD(month, b.duration, b.loan_date) AS end_date,
       CASE WHEN b.status IN ('A','B') THEN 1 ELSE 0 END AS is_finished,
       CASE WHEN DATEADD(month, b.duration, b.loan_date) >= '1999-01-01' THEN 1 ELSE 0 END AS is_censored,
       CASE WHEN b.status IN ('B','D') THEN 1 ELSE 0 END AS is_bad
INTO clean.loan FROM b;
GO
-- k_symbol: NULL và chuỗi trắng gộp thành 'NONE'; operation giữ NULL nguyên trạng
DROP TABLE IF EXISTS clean.trans;
SELECT CAST(TRY_CONVERT(decimal(18,0), trans_id) AS int) AS trans_id,
       CAST(TRY_CONVERT(decimal(18,0), account_id) AS int) AS account_id,
       TRY_CONVERT(date, [date]) AS trans_date,
       [type],
       operation,
       TRY_CONVERT(decimal(18,2), amount) AS amount,
       TRY_CONVERT(decimal(18,2), balance) AS balance,
       ISNULL(NULLIF(LTRIM(RTRIM(k_symbol)), ''), 'NONE') AS k_symbol,
       bank AS partner_bank,
       CAST(TRY_CONVERT(decimal(18,0), account) AS bigint) AS partner_account
INTO clean.trans FROM stg.trans;
GO
CREATE CLUSTERED INDEX ix_trans_acc_date ON clean.trans (account_id, trans_date, trans_id);
GO
-- Bảng tra mã Czech (dịch theo tài liệu mô tả Berka, cần đối chiếu lại khi viết README)
DROP TABLE IF EXISTS clean.code_map;
CREATE TABLE clean.code_map (col varchar(20), code varchar(30), label_en varchar(70));
INSERT INTO clean.code_map VALUES
('type','PRIJEM','credit'),('type','VYDAJ','debit'),('type','VYBER','cash withdrawal (nhãn lệch, xem checks)'),
('operation','VKLAD','cash deposit'),('operation','PREVOD Z UCTU','incoming transfer'),
('operation','VYBER','cash withdrawal'),('operation','PREVOD NA UCET','outgoing transfer'),
('operation','VYBER KARTOU','credit card withdrawal'),
('k_symbol','UROK','interest credited'),('k_symbol','SLUZBY','statement fee'),
('k_symbol','SIPO','household payment'),('k_symbol','DUCHOD','old-age pension'),
('k_symbol','POJISTNE','insurance payment'),('k_symbol','UVER','loan payment'),
('k_symbol','SANKC. UROK','penalty interest'),('k_symbol','NONE','no symbol (NULL hoặc trắng)'),
('frequency','POPLATEK MESICNE','monthly issuance'),('frequency','POPLATEK TYDNE','weekly issuance'),
('frequency','POPLATEK PO OBRATU','issuance after transaction'),
('loan_status','A','finished, paid'),('loan_status','B','finished, not paid'),
('loan_status','C','running, OK so far'),('loan_status','D','running, in debt');
GO
