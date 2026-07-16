# Financial Twin — Saad

This file is the single source of truth for the user's financial profile.
It is parsed at backend startup by `backend/profile.py`. Edit the values here to
change the demo — no code changes required.

```yaml
name: Saad
age: 28
city: Riyadh
salary: 18000 SAR/month
savings: 250000 SAR
monthly_expenses: 9000 SAR
expense_breakdown:
  rent: 3500
  food: 1800
  transport: 900
  subscriptions: 300
  other: 2500
assets:
  - Investment account: 40000 SAR
liabilities:
  - Personal loan: 1200 SAR/month, 18 months remaining
emergency_fund_target: 6 months of expenses (54000 SAR)
goals:
  - Buy a car (~120000 SAR) within 12 months
  - Umrah trip: 8000 SAR
risk_tolerance: moderate
ar_labels:
  Saad: سعد
  Riyadh: الرياض
  moderate: معتدلة
  Buy a car: شراء سيارة
  Umrah trip: رحلة عمرة
  Personal loan: قرض شخصي
  Investment account: حساب استثماري
  rent: الإيجار
  food: الطعام
  transport: المواصلات
  subscriptions: الاشتراكات
  other: أخرى
```

## Notes

- `ar_labels` holds Arabic display names only. **No numbers live there** — every figure has
  exactly one source of truth, above. To add another language, add another `xx_labels` block
  and register it in `backend/i18n.py`.
- `savings` is liquid cash. The investment account is tracked under `assets` and is
  deliberately **not** counted as emergency-fund cover (it is not instantly liquid).
- `emergency_fund_target` is derived: 6 x monthly_expenses = 54,000 SAR.
- Baseline monthly surplus = salary - expenses - debt payments
  = 18,000 - 9,000 - 1,200 = **7,800 SAR/month**.
