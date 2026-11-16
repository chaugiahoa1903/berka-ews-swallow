# Data quality report (staging, Berka qua CTU relational repository)

## Cột có null (toàn bộ bảng)
```
   table    column    rows  nulls  null_pct
   trans operation 1056320 183114     17.34
   trans  k_symbol 1056320 481881     45.62
   trans      bank 1056320 782812     74.11
   trans   account 1056320 760931     72.04
   order  k_symbol    6471   1379     21.31
district       A12      77      1      1.30
district       A15      77      1      1.30
```

## trans.type
```
 value      n
 VYDAJ 634571
PRIJEM 405083
 VYBER  16666
```

## trans.operation
```
         value      n
         VYBER 434918
PREVOD NA UCET 208283
        <NULL> 183114
         VKLAD 156743
 PREVOD Z UCTU  65226
  VYBER KARTOU   8036
```

## trans.k_symbol
```
      value      n
     <NULL> 481881
       UROK 183114
     SLUZBY 155832
       SIPO 118065
             53433
     DUCHOD  30338
   POJISTNE  18500
       UVER  13580
SANKC. UROK   1577
```

## Trùng khóa chính (0 là tốt)
```
  table        key  duplicates
account account_id           0
 client  client_id           0
   disp    disp_id           0
  trans   trans_id           0
  order   order_id           0
   loan    loan_id           0
   card    card_id           0
```

## Khoảng ngày
```
    tbl   min_date   max_date
  trans 1993-01-01 1998-12-31
   loan 1993-07-05 1998-12-08
account 1993-01-01 1997-12-29
```

## Mồ côi khóa ngoại (0 là tốt)
```
             chk  orphans
 loan -> account        0
trans -> account        0
```

## loan: status và số khoản chưa kết thúc theo ngày (date + duration >= 1999-01-01)
```
status   n  unfinished_by_date
     A 203                   0
     B  31                   0
     C 403                 403
     D  45                  45
```
