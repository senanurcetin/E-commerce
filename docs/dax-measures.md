# Power BI DAX Measures

50 measures across mart tables and disconnected parameter tables.
Model: `dim_user` → `fct_order_marketing` ← `dim_products` | `fct_marketing_web_performance`

---

## Data Model

| Table | Type | Role |
|-------|------|------|
| `fct_order_marketing` | Fact | Orders, revenue, returns |
| `fct_marketing_web_performance` | Fact | Sessions, conversions |
| `dim_user` | Dimension | Demographics, age segment, channel |
| `dim_products` | Dimension | Category, margin |
| `Analiz Metriği` | Disconnected | Field parameter — dynamic metric switcher |
| `Acquisition Metric` | Disconnected | Field parameter — acquisition KPI switcher |
| `Measurement Table` | Disconnected | Dynamic axis / title resolver |

---

## Core KPI Measures

```dax
Total Orders =
COUNTROWS(fct_order_marketing)

Toplam Gelir (Uyumlu Dönem) =
-- Time-aligned revenue; respects date slicer boundaries on both fact tables
CALCULATE(
    SUM(fct_order_marketing[revenue]),
    USERELATIONSHIP(fct_order_marketing[order_date], 'Calendar'[Date])
)

Müşteri Başına Gelir =
DIVIDE(
    SUM(fct_order_marketing[revenue]),
    DISTINCTCOUNT(fct_order_marketing[user_id])
)

ARPU =
-- Average Revenue Per User across all active users in period
DIVIDE(
    SUM(fct_order_marketing[revenue]),
    DISTINCTCOUNT(fct_order_marketing[user_id])
)

Ortalama Sepet Bedeli =
AVERAGE(fct_order_marketing[sale_price])

Dönüşüm Oranı =
DIVIDE(
    CALCULATE(COUNTROWS(fct_marketing_web_performance),
              fct_marketing_web_performance[is_converted] = 1),
    COUNTROWS(fct_marketing_web_performance)
)

Conversion Rate = [Dönüşüm Oranı]

Toplam Oturum =
COUNTROWS(fct_marketing_web_performance)

Müşteri Başına Oturum (CAC Proxy) =
DIVIDE(
    COUNTROWS(fct_marketing_web_performance),
    DISTINCTCOUNT(fct_marketing_web_performance[user_id])
)

Oturum Başına Gelir =
DIVIDE(
    SUM(fct_order_marketing[revenue]),
    COUNTROWS(fct_marketing_web_performance)
)

Revenue per Conversion =
DIVIDE(
    SUM(fct_order_marketing[revenue]),
    CALCULATE(COUNTROWS(fct_marketing_web_performance),
              fct_marketing_web_performance[is_converted] = 1)
)

Sessions per Conversion =
DIVIDE(
    COUNTROWS(fct_marketing_web_performance),
    CALCULATE(COUNTROWS(fct_marketing_web_performance),
              fct_marketing_web_performance[is_converted] = 1)
)
```

---

## Customer Acquisition Measures

```dax
İlk Sipariş Müşteri Sayısı =
-- New customers: users whose first-ever order falls within the current filter context
CALCULATE(
    DISTINCTCOUNT(fct_order_marketing[user_id]),
    FILTER(
        fct_order_marketing,
        fct_order_marketing[order_date] =
            CALCULATE(MIN(fct_order_marketing[order_date]),
                      ALLEXCEPT(fct_order_marketing, fct_order_marketing[user_id]))
    )
)

First Purchase Conversion Rate =
DIVIDE([İlk Sipariş Müşteri Sayısı], DISTINCTCOUNT(fct_marketing_web_performance[user_id]))

Aynı Gün Satın Alan Kullanıcılar =
-- Users who converted on the same calendar day as their first session
CALCULATE(
    DISTINCTCOUNT(fct_order_marketing[user_id]),
    FILTER(
        fct_order_marketing,
        fct_order_marketing[order_date] =
            CALCULATE(MIN(fct_marketing_web_performance[session_date]),
                      ALLEXCEPT(fct_marketing_web_performance,
                                fct_marketing_web_performance[user_id]))
    )
)

Aynı Gün Satın Alan Oranı =
DIVIDE([Aynı Gün Satın Alan Kullanıcılar], [İlk Sipariş Müşteri Sayısı])
```

---

## Margin Measures

```dax
Total Margin =
SUMX(
    fct_order_marketing,
    fct_order_marketing[revenue] -
    RELATED(dim_products[cost])
)

Total Margin % =
DIVIDE([Total Margin], SUM(fct_order_marketing[revenue]))

Return Rate =
DIVIDE(
    SUM(fct_order_marketing[returned_revenue]),
    SUM(fct_order_marketing[revenue]) + SUM(fct_order_marketing[returned_revenue])
)
```

---

## PE4 Channel Scorecard

Weighted composite scoring channel efficiency (0–100). Built across three pages with dynamic titles that update based on the selected channel filter.

```dax
PE4 Verimlilik Skoru =
-- 40% conversion quality + 40% revenue quality + 20% acquisition efficiency
VAR cvr_weight =
    DIVIDE([Dönüşüm Oranı],
           CALCULATE([Dönüşüm Oranı],
                     ALL(fct_marketing_web_performance[channel_group]))) * 40

VAR rev_weight =
    DIVIDE([Müşteri Başına Gelir],
           CALCULATE([Müşteri Başına Gelir],
                     ALL(fct_order_marketing[channel_group]))) * 40

VAR cac_weight =
    DIVIDE(CALCULATE([Müşteri Başına Oturum (CAC Proxy)],
                     ALL(fct_marketing_web_performance[channel_group])),
           [Müşteri Başına Oturum (CAC Proxy)]) * 20  -- inverted: fewer sessions = efficient

RETURN MIN(ROUND(cvr_weight + rev_weight + cac_weight, 0), 100)

PE4 Kanal Rolü =
-- Text label used in scorecard table
SWITCH(
    TRUE(),
    [PE4 Verimlilik Skoru] >= 80, "Öncelik: ölçekle",
    [PE4 Verimlilik Skoru] >= 50, "Optimize et",
    "Büyüt: hacim düşük"
)

PE4 Karar Sinyali = [PE4 Kanal Rolü]

PE4 Oturum Verimlilik Farkı =
-- Deviation of channel's sessions/customer from the overall average
[Müşteri Başına Oturum (CAC Proxy)]
- CALCULATE([Müşteri Başına Oturum (CAC Proxy)],
            ALL(fct_marketing_web_performance[channel_group]))

PE4 Skor Kartı Detay =
-- Multi-line text for the scorecard detail column
"Rol: " & [PE4 Kanal Rolü] & UNICHAR(10) &
"Yeni: " & FORMAT([İlk Sipariş Müşteri Sayısı], "#,0") &
" | Dönüşüm: " & FORMAT([Dönüşüm Oranı], "0.0%") & UNICHAR(10) &
"Gelir/Müş.: $" & FORMAT([Müşteri Başına Gelir], "#,0.00") &
" | Oturum/Müş.: " & FORMAT([Müşteri Başına Oturum (CAC Proxy)], "#,0.00") & UNICHAR(10) &
"Ort. fark: " & FORMAT([PE4 Oturum Verimlilik Farkı], "+#,0.00;-#,0.00")
```

---

## Dynamic Titles (Measurement Table + Field Parameters)

The `Analiz Metriği` and `Acquisition Metric` tables are **disconnected field parameter tables** that drive dynamic chart titles and axis labels based on slicer selection.

```dax
Dinamik Eksen İsmi =
SELECTEDVALUE('Analiz Metriği'[Analiz Metriği], "Metrik")

PE4 Main Chart Title =
"Edinim Verimliliği | " & [Dinamik Eksen İsmi]

PE4 Scorecard Title =
"Yönetici Skor Kartı | Kanal Karşılaştırması"

Pazarlama Kanalı TR (Ölçü) =
SWITCH(
    SELECTEDVALUE(fct_order_marketing[channel_group]),
    "paid",    "Ücretli",
    "owned",   "Sahipli",
    "organic", "Organik",
    "other",   "Diğer",
    "Tüm Kanallar"
)

Cinsiyet Dağılımı Başlığı =
"Tüm Kanallar Genelinde Cinsiyete Göre Toplam Ciro Dağılımı"

Müşteri Tipi Başlığı =
"Tüm Kanallar Genelinde Müşteri Tipine Göre Toplam Ciro Oranı"
```

---

## Notes

- `DIVIDE()` used throughout instead of `/` — handles zero denominators safely.
- `ALL()` / `ALLEXCEPT()` removes filter context for ratio denominators and period-level baselines.
- Disconnected tables (`Analiz Metriği`, `Acquisition Metric`) use field parameters — no relationship to fact tables, controlled by slicers only.
- `UNICHAR(10)` inserts line breaks inside card/table text measures.
- `PE4 Skor Kartı Detay` is a formatted multi-line string measure, not a numeric value.
