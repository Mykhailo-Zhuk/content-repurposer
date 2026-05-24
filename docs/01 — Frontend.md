---
tags: [ope-167, frontend, nextjs, typescript, tailwind, react-hook-form]
created: 2026-05-17
status: active
relates-to: "[[00 — OPE-167 Огляд проекту]]"
---

# 01 — Frontend

## Технологічний стек

| Бібліотека | Версія | Роль |
|---|---|---|
| Next.js | 14.2 | App Router, SSR, rewrites до API |
| TypeScript | 5 | Типізація |
| Tailwind CSS | 3.4 | Стилі |
| react-hook-form | 7.51 | Керування формою |
| Zod | 3.23 | Схема валідації URL |
| @hookform/resolvers | 3.4 | Zod ↔ react-hook-form bridge |
| TanStack Query | 5.40 | Polling статусу job |
| lucide-react | 0.383 | Іконки |
| clsx + tailwind-merge | — | Утиліта cn() для класів |

## Структура компонентів

```
src/
├── app/
│   ├── layout.tsx          # Root layout, metadata
│   ├── page.tsx            # Головна сторінка (єдина)
│   ├── providers.tsx       # QueryClientProvider
│   └── globals.css         # Tailwind + кастомні шрифти + анімації
├── components/
│   ├── features/
│   │   ├── SubmitForm.tsx  # Форма введення URL
│   │   └── JobStatusCard.tsx # Прогрес + результат + завантаження
│   └── ui/
│       └── ProgressBar.tsx # Анімований прогрес-бар
├── hooks/
│   └── useJobPolling.ts    # TanStack Query polling хук
└── lib/
    ├── api.ts              # HTTP клієнт (submitJob, getJobStatus)
    ├── schemas.ts          # Zod схема для URL
    └── utils.ts            # cn() утиліта
```

## Головна сторінка (`page.tsx`)

Єдина сторінка додатку. Два стани:

```
jobId === null  →  показати <SubmitForm />
jobId !== null  →  показати <JobStatusCard /> з polling
```

**UX flow:**
1. Користувач вводить YouTube URL
2. `SubmitForm` валідує через Zod, відправляє `POST /api/jobs/`
3. Отримує `job_id`, передає у стан
4. `useJobPolling` починає polling кожні 2 сек
5. `JobStatusCard` показує прогрес кроків + progress bar
6. Після `done` — кнопка завантаження + title/description/tags
7. Кнопка "Обробити інше відео" скидає `jobId`

## SubmitForm

```tsx
// Валідація Zod:
const submitSchema = z.object({
  url: z.string().regex(
    /^https:\/\/(www\.)?(youtube\.com\/watch\?v=[\w-]{11}|youtu\.be\/[\w-]{11})/,
    "Введіть коректне YouTube посилання"
  ),
});
```

**Особливості:**
- `disabled` під час `isSubmitting`
- Помилки сервера через `setError("url", ...)`
- Іконка `<Youtube />` зліва в полі вводу
- Hint внизу: "Ліміт: 5 відео на день · max 30 хв · потрібні субтитри"

## JobStatusCard

Показує поточний крок і прогрес:

| Статус | Крок | Прогрес |
|---|---|---|
| `queued` | Черга | 0% |
| `downloading` | Завантаження | 10% |
| `analyzing` | AI аналіз | 40–60% |
| `rendering` | Рендер | 75% |
| `done` | Готово | 100% |
| `failed` | Помилка | — |

**Компоненти всередині:**
- `ProgressBar` — анімований (shimmer ефект поки не `done`)
- Dots-steps — 5 кроків з підписами
- При `done`: title, description, теги, кнопка Download
- При `failed`: помилка у червоній плашці

## useJobPolling хук

```ts
useQuery({
  queryKey: ["job", jobId],
  queryFn: () => getJobStatus(jobId!),
  enabled: !!jobId,
  refetchInterval: (query) => {
    const status = query.state.data?.status;
    if (!status || ["done", "failed"].includes(status)) return false;
    return 2000; // кожні 2 секунди
  },
})
```

Polling автоматично зупиняється на `done` або `failed`.

## API клієнт (`api.ts`)

```ts
// Відправити URL
submitJob(url: string): Promise<SubmitResponse>

// Перевірити статус
getJobStatus(jobId: string): Promise<JobStatusResponse>

// URL для завантаження
getDownloadUrl(jobId: string): string  // → /api/jobs/{id}/download
```

## Next.js rewrites

`next.config.mjs` проксує всі `/api/*` запити до бекенду:

```js
async rewrites() {
  return [{
    source: "/api/:path*",
    destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
  }];
}
```

Завдяки цьому фронтенд і бекенд живуть на різних портах без CORS-проблем у dev режимі.

## Дизайн

| Параметр | Значення |
|---|---|
| Тема | Dark (фон #0A0A0A) |
| Акцентний колір | #FF3D00 (бренд-помаранчевий) |
| Display шрифт | Barlow Condensed (700, 900) — через Google Fonts |
| Body шрифт | DM Sans (400, 500) |
| Анімації | CSS keyframes: slideUp, fadeIn, progress-shine |

## Змінні оточення

| Змінна | Обов'язкова | Опис |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Так | URL бекенду (напр. `http://localhost:8000`) |

## Обробка помилок

| Ситуація | Поведінка |
|---|---|
| Невалідний URL | Zod помилка під полем вводу |
| Rate limit (429) | Повідомлення: "Ліміт на сьогодні вичерпано" |
| Сервер недоступний | `setError` з повідомленням "Помилка сервера" |
| Job `failed` | Червона плашка з текстом помилки від бекенду |
| Polling помилка | TanStack Query retry 3 рази |

## Пов'язані нотатки

- [[02 — Backend і API]]
- [[06 — Запуск та автоматизація]]
