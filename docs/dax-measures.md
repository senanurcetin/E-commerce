# Power BI DAX Measures

DAX measures used across the three dashboard pages. All measures reference
`fct_order_marketing` or `fct_marketing_web_performance` mart tables.

---

## Core KPI Measures

```dax
-- New customers: unique users with at least one delivered order
New Customers =
CALCULATE(
    DISTINCTCOUNT(fct_order_marketing[user_id]),
    fct_order_marketing[is_completed_order] = 1
)

-- Revenue per customer (LTV proxy)
Revenue Per Customer =
DIVIDE(
    SUM(fct_order_marketing[revenue]),
    DISTINCTCOUNT(fct_order_marketing[user_id])
)

-- Conversion rate: sessions that resulted in a purchase
Conversion Rate =
DIVIDE(
    CALCULATE(COUNTROWS(fct_marketing_web_performance),
              fct_marketing_web_performance[is_converted] = 1),
    COUNTROWS(fct_marketing_web_performance)
)

-- Sessions per customer (CAC proxy: higher = more touchpoints before purchase)
Sessions Per Customer =
DIVIDE(
    COUNTROWS(fct_marketing_web_performance),
    DISTINCTCOUNT(fct_marketing_web_performance[user_id])
)
```

---

## Channel Efficiency Measures

```dax
-- Net revenue (excluding returns)
Net Revenue =
SUM(fct_order_marketing[revenue])
    - SUM(fct_order_marketing[returned_revenue])

-- Return rate by channel
Return Rate =
DIVIDE(
    COUNTROWS(FILTER(fct_order_marketing, fct_order_marketing[is_returned_order] = 1)),
    COUNTROWS(fct_order_marketing)
)

-- Average session duration in minutes
Avg Session Duration (min) =
AVERAGE(fct_marketing_web_performance[session_duration_minutes])
```

---

## PE4 Efficiency Score (Custom Scorecard Measure)

The scorecard ranks channels 0–100 using a weighted composite of:
- Conversion rate (40%)
- Revenue per customer (40%)
- Sessions per customer (20%, inverted — lower = more efficient)

```dax
PE4 Efficiency Score =
VAR cvr_score =
    DIVIDE(
        [Conversion Rate],
        CALCULATE([Conversion Rate], ALL(fct_marketing_web_performance[channel_group]))
    ) * 40

VAR rev_score =
    DIVIDE(
        [Revenue Per Customer],
        CALCULATE([Revenue Per Customer], ALL(fct_order_marketing[channel_group]))
    ) * 40

VAR cac_score =
    DIVIDE(
        CALCULATE([Sessions Per Customer], ALL(fct_marketing_web_performance[channel_group])),
        [Sessions Per Customer]
    ) * 20   -- inverted: lower sessions per customer = more efficient

RETURN
    MIN(ROUND(cvr_score + rev_score + cac_score, 0), 100)
```

---

## Time Intelligence

```dax
-- Year-over-year revenue growth
Revenue YoY % =
VAR current_year = SUM(fct_order_marketing[revenue])
VAR prior_year =
    CALCULATE(
        SUM(fct_order_marketing[revenue]),
        DATEADD(fct_order_marketing[order_date], -1, YEAR)
    )
RETURN
    DIVIDE(current_year - prior_year, prior_year)

-- Baseline deviation (actual vs period average)
Avg Deviation =
[Revenue Per Customer]
- CALCULATE(
    [Revenue Per Customer],
    ALL(dim_user[country], dim_user[gender], dim_user[age_segment])
  )
```

---

## Notes

- All measures use `DIVIDE()` instead of `/` to handle divide-by-zero safely.
- `ALL()` removes filter context when computing totals for ratio denominators.
- The PE4 score is bounded to 100 with `MIN()` to avoid >100 on small segments.
