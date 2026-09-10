# ECI v6.0 OMNIVERSE — Hyper-Architecture

> ارتقای پیشرفته در همه لایه‌ها + افزودن هر سیستمی که کم بود.

## چه چیزی اضافه شد (۱۴ زیرسیستم جدید)

| لایه | ماژول | نقش |
|---|---|---|
| Kernel | `kernel/bus.py` | EventBus با wildcard، DLQ، replay، correlation/causation |
| Kernel | `kernel/container.py` | DI با تشخیص چرخه + override تستی |
| Kernel | `kernel/lifecycle.py` | استارت/استاپ ترتیبی با DAG وابستگی + health تجمیعی |
| Ops | `observability/` | Tracer + MetricsRegistry (Prometheus) + AuditLogger زنجیره‌هش |
| Ops | `persistence/` | EventStore (memory/sqlite) + Repository + UnitOfWork |
| Ops | `resilience/` | CircuitBreaker + RetryPolicy + TokenBucket + Saga جبرانی |
| Ops | `streaming/` | Topic bus با backpressure + consumer-group + replay |
| Control | `orchestration/` | DAG (سطوح موازی، retry/timeout) + Scheduler اولویت‌دار/پریودیک |
| Control | `plugins/` | PluginManager با capability allowlist + ترتیب وابستگی |
| Control | `authz/` | RBAC + PolicyEngine (ABAC روی Protocol-0، deny-closed) |
| Control | `tenancy/` | Namespace + Quota + admission |
| Intel | `mlops/` | ModelRegistry (version/stage/lineage) + drift (PSI/KS) |
| Intel | `provenance/` | گراف علی تصمیم‌ها + lineage + explain |
| Intel | `api/` | Gateway نسخه‌دار با auth/rate/trace/audit + schema |
| Security | `security/secrets.py` | SecretManager رمزنگاری‌شده + rotation + TTL |
| Security | `security/secure_channel.py` | HybridSecureChannel: سوکت واقعی/TLS-ready + سیل ML-KEM |
| Chaos | `chaos/` | Fault plans اعلانی با guardrail و abort خودکار |

## سیم‌کشی

- `ECIFramework` (v6 OMNIVERSE): همه سیستم‌ها را می‌سازد، به lifecycle و container
  وصل می‌کند، پالیسی‌ها و روت‌های پیش‌فرض (`v1/ping`, `v1/system.status`) را نصب می‌کند.
- `ECIConfig`: سکشن‌های `kernel/observability/persistence/resilience/api` +
  `feature_flags` + `from_env()` (overlay متغیر محیطی `ECI_<SEC>_<FIELD>`).
- CLI: `eci system` (اسنپ‌شات کامل سلامت) و `eci workflow` (برش end-to-end:
  DAG → bus → stream → provenance → audit).
- `eci/__init__.py`: صادرات ۳۰+ نماد جدید (مجموع ۱۷۰+).

## قراردادهای کلیدی

- **Deny-closed**: authz بدون rule صریح → deny (امن).
- **Fail-fast + جبران**: breaker مدار را باز می‌کند؛ saga جبران معکوس می‌زند.
- **Backpressure**: ناشر هیچ‌وقت بلاک نمی‌شود؛ `dropped` شمرده می‌شود.
- **Tamper-evident**: audit زنجیره‌هش دارد (`verify()`).
- **Replayable**: event-store + provenance هر تصمیم را بازپخش‌پذیر می‌کند.

## اجرا

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m eci system
PYTHONPATH=src python -m eci workflow
```
