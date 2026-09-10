# AGI Cognition Stack (v6.2 AGI-DAWN)

> آینده‌نگرانه، خلاقانه، دقیق — و صادقانه درباره مرزها.

## ایده مرکزی

AGI نه از scale خالص، بلکه از **حلقه شناخت کامل** می‌آید:
جهان‌مدل (تصور) → کنجکاوی (اشتها) → برنامه‌ریز (تدبیر) → منشور (وجدان) →
اجرا (فراشناخت) → رؤیا (تحکیم) → علم (کشف) → ذهن‌خوانی (هماهنگی).

## ماژول‌ها (`src/eci/cognition/`)

| ماژول | نقش دقیق | صداقت عددی |
|---|---|---|
| `world_model.py` | RSSM-lite: GRU + نهان گاوسی + انسامبل دینامیک؛ `imagine()` غلتان آینده | تک‌نمایی/هموار؛ چندنمایی نیازمند نهان گسسته است |
| `planner.py` | CEM روی آینده‌های تصورشده؛ بودجه تطبیقی System-1/2 از عدم‌قطعیت | horizon کوتاه؛ افق بلند نیازمند سلسله‌مراتب است |
| `curiosity.py` | RND-lite + disagreement + surprise با نرمال‌سازی Welford خودکالیبره |–|
| `consolidation.py` | خواب: گزینش salient، تقطیر به حافظه برداری، فراموشی Ebbinghaus، replay زاینده | – |
| `causal.py` | کشف PC-lite (lag + partial correlation + Fisher-z)؛ **ATE پس‌درِ lag-aware** با lag گزارش‌شده | پروکسی خطی-گاوسی؛ بدون تضمین confounding پنهان (نه FCI) |
| `scientist.py` | رقابت فرضیه‌ها با BIC، طراحی max-variance، به‌روزرسانی مزدوج گاوسی، آستانه ارتقا به commons | – |
| `tom.py` | مدل همتایان level-1، Brier-score، سیم‌خاردار فریب (challenge + provenance) | عمق بازگشتی محدود به ۱ (مستند) |
| `charter.py` | سلسله‌مراتب ۷ وظیفه (corrigibility اول)؛ کامپایل به policy؛ اصلاح فقط با ابراکثریت DAO + دادگاه | – |
| `executive.py` | ECE کالیبراسیون، استراتژی stakes×uncertainty، دفتر تعهدات + رانش، داوری court/market/dao | – |

## `think()` — یک ضربان شناختی

```
charter.check → refuse? | uncertainty probe → strategy(fast/deliberate/council)
→ CEM plan over imagine() → curiosity top-up → provenance + bus record
```

## اجرا

```bash
PYTHONPATH=src python -m eci think --goal "stabilize" --stakes 0.4
PYTHONPATH=src python -m eci dream --episodes 16
PYTHONPATH=src pytest tests/test_cognition.py -q
```

## مسیر آینده (صادقانه)

نهان گسسته چندنمایی → برنامه‌ریز سلسله‌مراتبی → FCI علّی → PyPhi واقعی در
حلقه → embodiment حسی-حرکتی. هرکدام با گیت رگرسیون خودش وارد می‌شود، نه با شعار.
