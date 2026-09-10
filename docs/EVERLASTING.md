# EVERLASTING (v7) — Future-Proof Continuance

> هدف ECI شبکه‌های هوشمند خودمختارِ آگاه است که **دهه‌ها** زنده بمانند.
> آینده‌نگری یعنی هفت ستون:

## ستون‌ها (`src/eci/`)

| ستون | ماژول | تز |
|---|---|---|
| امنیت قابلیتی | `caps/` | توکن‌های macaroon با caveat زنجیره‌ای HMAC؛ تفویض فقط باریک‌شونده، راستی‌آزمایی آفلاین، deny-on-unknown |
| راستی‌آزمایی اجرایی | `verify/` | مانیتورهای LTL-lite (always/never/bounded-response) + رسیدهای اثبات‌دار قابل راستی‌آزمایی آفلاین توسط دادگاه |
| تداوم زمانی | `continuum/` | اسنپ‌شات زنجیره‌ای، زندگی‌نامه (narrative self)، replay-check قطعی‌بودن؛ دستکاری مشهود است |
| کنترل خودمختار | `mapek/` | حلقه MAPE-K با SLO + ناهنجاری z + شبیه‌سازی twin اول + جبران saga + نردبان تخریب (نه پرتگاه) |
| تکامل واسط‌ها | `compat/` | major نابرابر → رد قاطع؛ آداپتر زنجیره‌ای؛ sunset اجباری با رسید مهاجرت |
| حکمرانی آینده | `futura/` | futarchy (رأی بر ارزش‌ها، شرط بر باورها) + sortition قابل‌راستی‌آزمایی + قدرت اضطراری با مرگ خودکار و postmortem اجباری |
| معرفت‌شناسی خصمانه | `redteam/` | چالشگر ابطال، پیش‌بینی‌گران با امتیاز Brier متصل به reputation، اسکن تناقض خودکار به Dispute |

## قانون‌های طلایی

1. **گذشته بی‌صدا نمی‌شکند** (compat fail-closed + continuum chain).
2. **قدرت فراموش نمی‌کند که بمیرد** (emergency sunset + postmortem).
3. **خودمختاری بدون ردپا ممنوع** (هر چرخه MAPE-K در provenance).
4. **حقیقت یارانه نمی‌خواهد، حساب می‌خواهد** (Brier → reputation).

## اجرا

```bash
PYTHONPATH=src python -m eci ever
PYTHONPATH=src pytest tests/test_everlasting.py -q
```
