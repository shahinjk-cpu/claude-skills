# Антиспам через Cloudflare Turnstile и Edge Function

- [Шлюз](#шлюз)
- [Ключи, CORS и CSP](#ключи-cors-и-csp)
- [Клиент](#клиент)
- [Выкатка](#выкатка) и [откат](#откат)
- [Грабли](#грабли)
- [Как проверить](#как-проверить)

```text
Браузер → виджет Turnstile → одноразовый токен
Браузер → POST /functions/v1/turnstile-gate { action, token, payload }
Шлюз   → Cloudflare Siteverify → success, action, hostname
Шлюз   → PostgREST под service_role → place_order(jsonb)
```

URL Supabase и anon key публичны. Пока у браузерных ролей есть `EXECUTE`,
клиентский виджет можно пропустить, вызвав RPC напрямую. Защита включается
целиком после двух изменений: шлюз требует валидный токен, база отзывает прямой
доступ. Проверьте все перегрузки и другие пути к той же записи по
`references/supabase-audit.md`.

## Шлюз

Возьмите `assets/turnstile-gate.ts` как `supabase/functions/turnstile-gate/index.ts`.
В `ACTIONS` оставьте только публичные операции, которым нужна капча. Ключ
`order` — значение `action` в виджете и JSON запроса. `rpc` — имя функции
в базе, `args` преобразует тело запроса в именованные параметры PostgREST.

```ts
const ACTIONS: Record<string, Action> = {
  order: {
    rpc: "place_order",
    args: ({ payload }) =>
      payload && typeof payload === "object" && !Array.isArray(payload)
        ? { payload }
        : null,
  },
};
```

Имя RPC и набор аргументов определяет сервер. Сверяйте типы, размеры и обязательные
поля. Проверки цены, доступности, лимитов и идемпотентности оставьте в RPC.
`service_role` обходит RLS, поэтому публичный шлюз подходит для узких операций
вроде создания заказа. Пользовательские операции, зависящие от `auth.uid()`,
требуют отдельной проверки личности и прав. Turnstile пользователя не идентифицирует.

До вызова RPC шлюз сверяет `success === true`, `action` с ключом из `ACTIONS`
и `hostname` с разрешёнными хостами. Проверка действия связывает токен с
операцией, проверка хоста — с сайтом. При таймауте или ошибке Siteverify
RPC не вызывается. Используйте строгую проверку хоста даже при ошибке настройки:
пустой список хостов должен блокировать запросы. В `verifyTurnstile` замените
условную проверку списка на `if (!ALLOWED_HOSTS.includes(v.hostname)) return false;`.
[Cloudflare Siteverify](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)

Для контракта «без токена → 403» замените в шаблоне проверку
`if (!action || !token || token.length > 2048)`. В исходном ассете отсутствие
токена даёт `400`.

```ts
if (!action || token.length > 2048) {
  return reply({ message: "bad request" }, 400, origin);
}
if (!token) return reply({ message: "captcha required" }, 403, origin);
```

## Ключи, CORS и CSP

- В Cloudflare создайте виджет Managed. Укажите хосты сайта, например
  `my-site.vercel.app`. В браузерный `config.js` идёт только публичный
  `TURNSTILE_SITE_KEY`.
- В Edge Function Secrets задайте `TURNSTILE_SECRET_KEY` и `ALLOWED_ORIGINS`
  (список через запятую, например `https://my-site.vercel.app`). Origin включает
  схему и порт, если он нестандартный. Путь и завершающий слеш уберите.
  `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY` шаблон читает из окружения Supabase.
  Сервисный ключ и секрет Turnstile держите на сервере.
- Обработайте `OPTIONS` до разбора тела. Разрешённому origin возвращайте его в
  `Access-Control-Allow-Origin` вместе с `Vary: Origin`. Разрешите заголовки,
  которые реально посылает клиент. Вне браузера заголовок `Origin` задаёт сам
  отправитель, поэтому CORS не заменяет Siteverify.
- Пример запросов ниже рассчитан на legacy anon JWT. С включённым
  `verify_jwt` платформа проверяет Bearer JWT до входа в функцию. Для публичного
  шлюза с современным publishable key передавайте его в `apikey` и задайте
  `verify_jwt = false` в секции `[functions.turnstile-gate]`. Сам шлюз
  по-прежнему требует Turnstile. Для RPC от вошедшего клиента Bearer — его
  access token. [Supabase Edge Function auth](https://supabase.com/docs/guides/functions/auth-headers)
- В CSP добавьте `https://challenges.cloudflare.com` в `script-src` и
  `frame-src`, а `https://<project-ref>.supabase.co` в `connect-src`
  (или фактический API origin). При `script-src-elem` проверьте и его.
  При `strict-dynamic` проверьте, что загрузчик виджета наследует доверие от
  разрешённого скрипта. Для режима pre-clearance добавьте `'self'` в `connect-src`.
  [Cloudflare CSP](https://developers.cloudflare.com/turnstile/reference/content-security-policy/)

## Клиент

Внешний скрипт сайта подключает `api.js?render=explicit`. Контейнер
`<div id="ts-order"></div>` разместите в открытой форме. Пример использует
`cfg.SUPABASE_URL`, `cfg.SUPABASE_ANON_KEY` и `cfg.TURNSTILE_SITE_KEY`
из конфигурации сайта.

```js
let turnstileReady;

function loadTurnstile() {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  return turnstileReady ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    const fail = () => {
      clearTimeout(timer);
      script.remove();
      reject(new Error("Не загрузилась проверка. Повторите попытку."));
    };
    const timer = setTimeout(fail, 15000);
    script.onload = () => {
      if (!window.turnstile) return fail();
      clearTimeout(timer);
      resolve(window.turnstile);
    };
    script.onerror = fail;
    document.head.append(script);
  }).catch(error => {
    turnstileReady = null;
    throw error;
  });
}

async function requestOrderToken() {
  const ts = await loadTurnstile();
  let widgetId;
  let timer;
  try {
    return await new Promise((resolve, reject) => {
      const fail = () => reject(new Error("Проверка не завершилась. Повторите попытку."));
      timer = setTimeout(fail, 60000);
      widgetId = ts.render("#ts-order", {
        sitekey: cfg.TURNSTILE_SITE_KEY,
        action: "order",
        appearance: "interaction-only",
        callback: resolve,
        "error-callback": fail,
        "expired-callback": fail,
      });
    });
  } finally {
    clearTimeout(timer);
    if (widgetId !== undefined) ts.remove(widgetId);
  }
}

let prepared;
let pending;
const gateOn = Boolean(cfg.TURNSTILE_SITE_KEY);
const fresh = () => prepared && Date.now() - prepared.at < 280_000;

// Вызовите при открытии формы. Покажите ошибку при отправке, если проверка снова не удалась.
function prepareOrderToken() {
  if (!gateOn || fresh()) return Promise.resolve();
  return pending ??= requestOrderToken()
    .then(token => { prepared = { token, at: Date.now() }; })
    .finally(() => { pending = null; });
}

async function submitOrder(payload) {
  let path = "/rest/v1/rpc/place_order";
  let body = { payload };

  if (gateOn) {
    await prepareOrderToken();
    if (!fresh()) throw new Error("Проверка устарела. Повторите попытку.");
    const { token } = prepared;
    prepared = null;
    path = "/functions/v1/turnstile-gate";
    body = { action: "order", token, payload };
  }

  const response = await fetch(cfg.SUPABASE_URL + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: cfg.SUPABASE_ANON_KEY,
      Authorization: "Bearer " + cfg.SUPABASE_ANON_KEY,
    },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => null);
  if (response.ok) return data;
  if (gateOn && response.status === 403) {
    throw new Error("Проверка отклонена. Повторите попытку.");
  }
  throw new Error("Сервер не принял заказ. Повторите попытку.");
}
```

При открытии формы вызовите `prepareOrderToken().catch(() => {})`. На submit
отключайте кнопку до завершения `submitOrder`, показывайте ошибку рядом с формой,
сохраняйте поля и открывайте следующую вкладку после успешной проверки.
Токен действует 300 секунд, один раз. Запас в 20 секунд оставляет время на
доставку запроса. Токен убирается из памяти до отправки: даже при потере ответа
он мог быть уже проверен. При повторе берите новый токен и сохраняйте ключ
идемпотентности заказа, если RPC его поддерживает.

Пустой site key включает прямой RPC для переходного периода и отката. После
lock-миграции он сработает только после восстановления гранта. При ошибке
виджета или шлюза фолбэк по статусу не делайте.

## Выкатка

1. **Выдать грант шлюзу.** Зафиксируйте исходные ACL и примените отдельную
   миграцию. Старый сайт продолжает пользоваться своими грантами.

   ```sql
   grant execute on function public.place_order(jsonb) to service_role;
   ```

2. **Настроить Cloudflare и секреты, выкатить шлюз.** Например,
   `supabase functions deploy turnstile-gate --project-ref <project-ref>`
   (подставьте значение без угловых скобок). Проверьте preflight, отказ без токена
   и успешный запрос через браузер на стенде. Проверьте старый маршрут сайта.
3. **Выкатить сайт с ключом и CSP.** На целевом домене проверьте каждое действие
   из `ACTIONS` и запись в базе. Учтите открытые вкладки и кэшированные
   `config.js` и JS: старая сборка продолжит вызывать RPC напрямую. Обновите
   ассеты на CDN и открытые вкладки до отзыва грантов.
4. **Применить lock отдельной миграцией.** Подставьте все нужные сигнатуры.
   Повторите браузерную проверку и проверьте отказ браузерным ролям.

   ```sql
   begin;
   revoke execute on function public.place_order(jsonb) from public, anon, authenticated;
   grant execute on function public.place_order(jsonb) to service_role;
   commit;
   ```

## Откат

Если lock уже применён, сначала верните прежние прямые гранты ролям,
которые использовал сайт. Например, если обе роли имели доступ:

```sql
grant execute on function public.place_order(jsonb) to anon, authenticated;
```

Затем очистите `TURNSTILE_SITE_KEY` и выкатите конфиг либо возвратите рабочую
прямую сборку. Проверьте заказ в новой вкладке. Пока старые вкладки используют
шлюз, сохраните его рабочую конфигурацию. Возврат прямых грантов снова открывает
операцию без капчи.

## Грабли

- Шлюз прошёл капчу, но получил `permission denied for function place_order`.
  У `service_role` отсутствовал `EXECUTE`. Проверяйте его отдельным грантом
  до деплоя фронта и до отзыва `PUBLIC`.
- Проверка стартовала после перехода в мессенджер. Если требовалось действие
  в виджете, пользователь его не видел, а запрос ждал до таймаута.
- Lock выкатили бы раньше сайта — старый клиент потерял бы маршрут. Грант,
  деплой клиента и lock должны быть отдельными шагами.
- Если сверять только `success`, потеряется привязка для другого действия или
  хоста. Тестовые ключи Cloudflare возвращают условный hostname и не возвращают
  action. Для проверки обеих привязок используйте отдельный реальный виджет
  на стенде. [Тестовые ключи Cloudflare](https://developers.cloudflare.com/turnstile/troubleshooting/testing/)
- Preview, кастомный домен и основной домен Vercel — разные origins. Проверьте
  оба списка (Cloudflare и `ALLOWED_ORIGINS`) и ответ на preflight.
  Если gateway отвечает `401` до функции, проверьте `verify_jwt` и тип ключа.

## Как проверить

На стенде с настроенным шлюзом и применённым lock. Перед запуском задайте
`SUPABASE_URL` и `ANON_JWT` для стенда. Origin должен быть разрешён.

```bash
curl -i "$SUPABASE_URL/functions/v1/turnstile-gate" \
  -H 'Origin: https://my-site.vercel.app' -H 'Content-Type: application/json' \
  -H "apikey: $ANON_JWT" -H "Authorization: Bearer $ANON_JWT" \
  --data '{"action":"order","payload":{}}'
# 403, captcha required

curl -i "$SUPABASE_URL/rest/v1/rpc/place_order" \
  -H 'Content-Type: application/json' \
  -H "apikey: $ANON_JWT" -H "Authorization: Bearer $ANON_JWT" \
  --data '{"payload":{}}'
# PostgreSQL 42501, permission denied for function place_order
```

В браузере проверьте preflight и успешную запись с новым токеном. В тесте
шлюза повторно подайте использованный токен и проверьте `403` и отсутствие новой
записи. Проверьте CSP в консоли и через `scripts/csp_scan.mjs` для inline-кода.

На стенде `scripts/pg-harness/` добавьте эту проверку в сценарий после подготовки
валидного заказа. Она проверяет права SQL; реальную проверку токена покрывает
тест шлюза.

```js
async function checkOrderGate(h, validOrder) {
  const sql = "select * from public.place_order($1::jsonb)";
  const args = [JSON.stringify(validOrder)];
  await h.rejects(h.asAnon(sql, args), /permission denied/);
  const uid = await h.createUser({ email: "customer@example.com" });
  await h.rejects(h.asUser(uid, sql, args), /permission denied/);
  const result = await h.asService(sql, args);
  h.assert.ok(result.rows[0]?.id); // адаптируйте к результату вашей RPC
}
```

Вызовите `await checkOrderGate(h, validOrder)` из `export default async function (h)`.
Запустите с полным порядком миграций и `--twice` для lock-файла.

```bash
node "$HARNESS/harness.mjs" --repo "$PROJECT" --scenario "$CHECKS" --twice turnstile_lock.sql
```

`HARNESS` — подготовленная копия `scripts/pg-harness/` после `sh setup.sh`,
`PROJECT` — каталог проекта, `CHECKS` — путь к сценарию. Если порядок в DEPLOY.md
не распознан, передайте `--migrations` со списком файлов через запятую.
