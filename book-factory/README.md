# AI Book Factory

خط تولید خودگردان و ابری برای نگارش کتاب فارسی با GitHub Actions و Gemini.

## بعد از راه‌اندازی چه اتفاقی می‌افتد؟

یک اجرای Workflow می‌تواند این چرخه را خودش انجام دهد:

```text
pending
  ↓
AI Writer
  ↓
written
  ↓
AI Reviewer
  ↓
approved ─────────┐
  ↑               │
revision_required│
  └── AI Writer ─┘
  ↓
XeLaTeX
  ↓
PDF
  ↓
GitHub Artifact + GitHub Release
```

فصل‌ها و گزارش بازبینی در خود repository commit می‌شوند. PDF نیز هم به‌صورت Artifact و هم Release asset منتشر می‌شود.

## تنها تنظیم ضروری

در repository یک Repository Secret با نام زیر بسازید:

```text
GEMINI_API_KEY
```

اختیاری: در `Settings → Secrets and variables → Actions → Variables` متغیر `GEMINI_MODEL` را تعریف کنید. مقدار پیش‌فرض پروژه `gemini-3.8-flash` است.

## اجرای خودکار

Workflow:

```text
.github/workflows/book_factory.yml
```

را یک بار از تب **Actions → AI Book Factory - Autonomous → Run workflow** اجرا کنید. با `max_chapters=0` تمام فصل‌های قابل پردازش را دنبال می‌کند؛ برای اجرای کنترل‌شده می‌توانید عدد مشخصی بدهید.

پس از آن، برنامه‌ی زمان‌بندی‌شده نیز می‌تواند چرخه را اجرا کند.

## نکته مهم درباره GitHub

من از داخل این گفتگو اتصال نوشتاری مستقیم به حساب GitHub شما ندارم؛ بنابراین نمی‌توانم به‌جای حساب شما اولین repository را بسازم یا اولین Push را انجام دهم. این محدودیت فقط مربوط به **Bootstrap اولیه** است. بعد از اینکه این پروژه داخل repository قرار گرفت و `GEMINI_API_KEY` ثبت شد، اجرای واقعی، Commit، Push، ساخت PDF و Release روی GitHub Actions انجام می‌شود و سیستم محلی شما Runtime نیست.

برای Bootstrap یک‌باره می‌توانید از GitHub CLI استفاده کنید:

```bash
gh auth login
gh repo create YOUR-REPO --private --source . --remote origin --push
```

یا ZIP را در یک repository تازه آپلود کنید.

## امنیت

کلید Gemini داخل repository قرار نمی‌گیرد و فقط از GitHub Secrets خوانده می‌شود. Workflow فقط `contents: write` دارد. `GITHUB_TOKEN` توسط GitHub برای هر job به‌صورت خودکار صادر می‌شود و عمر آن محدود به اجرای job است.

## فونت فارسی

Build از فونت‌های Noto موجود روی runner استفاده می‌کند. فونت‌های تجاری مانند B Zar/B Nazanin را بدون بررسی مجوز در repository عمومی قرار ندهید.
