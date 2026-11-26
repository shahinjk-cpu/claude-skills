# CSP и SRI для статического сайта

Цель — браузер загружает JavaScript из явно разрешённых источников, блокирует
исполняемые inline-скрипты и HTML-обработчики, а файлы с CDN проверяет по хэшу.
CSP снижает риск XSS. Динамические данные по-прежнему вставляйте через
`textContent` и DOM API или экранируйте по контексту. Права доступа к данным
проверяйте в Supabase по `references/supabase-audit.md`.

## Содержание

- [Целевая политика](#целевая-политика)
- [Перевод и выкатка](#перевод-и-выкатка)
- [CDN и SRI](#cdn-и-sri)
- [Остальные заголовки](#остальные-заголовки)
- [Грабли](#грабли)
- [Как проверить](#как-проверить)

## Целевая политика

Пример `vercel.json` для сайта с Supabase, Leaflet, Google Fonts и Turnstile.
Подставьте свой `<project-ref>`. Уберите источники компонентов, которых у вас нет.

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'; script-src 'self' https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.118.0/ https://unpkg.com/leaflet@1.9.4/ https://challenges.cloudflare.com; script-src-attr 'none'; style-src 'self' 'unsafe-inline' https://unpkg.com/leaflet@1.9.4/ https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://unpkg.com/leaflet@1.9.4/; frame-src https://challenges.cloudflare.com; connect-src https://<project-ref>.supabase.co wss://<project-ref>.supabase.co; form-action 'self'; upgrade-insecure-requests"
        },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "geolocation=(self), camera=(), microphone=(), payment=()" },
        { "key": "Strict-Transport-Security", "value": "max-age=31536000" }
      ]
    },
    {
      "source": "/track.html",
      "headers": [
        { "key": "Cache-Control", "value": "no-store" },
        { "key": "Referrer-Policy", "value": "no-referrer" }
      ]
    }
  ]
}
```

| Директива | Зачем |
|---|---|
| `default-src 'self'` | Запасное правило для типов ресурсов без отдельной директивы. Явная директива заменяет этот список целиком. |
| `base-uri 'none'` | Запрещает `<base>`, который меняет разрешение относительных URL. |
| `frame-ancestors 'none'` | Запрещает встраивать страницу сайта во фрейм. Передавайте в HTTP-заголовке. |
| `object-src 'none'` | Запрещает загрузку через `<object>` и `<embed>`. |
| `script-src` | Разрешает локальные JS, указанные каталоги CDN и SDK Turnstile. Без `'unsafe-inline'` блокирует исполняемые inline-скрипты, без `'unsafe-eval'` — компиляцию JS из строк. |
| `script-src-attr 'none'` | Блокирует `onclick`, `onchange`, `onerror` и остальные HTML-обработчики, в том числе вставленные после загрузки страницы. |
| `style-src` | Разрешает локальный CSS, CSS карты и Google Fonts. `'unsafe-inline'` оставлен для `<style>`, атрибутов `style=` и библиотек, которые их создают. Разрешение действует только на стили. |
| `font-src` | Разрешает файлы шрифтов с сайта и `fonts.gstatic.com`. CSS Google Fonts загружается по `style-src` с другого хоста. |
| `img-src` | Разрешает локальные изображения, `data:` для встроенных картинок, тайлы и иконки Leaflet из его CSS. Оставьте только фактические хосты тайлов. Для изображений из Supabase Storage добавьте их источник сюда. |
| `frame-src` | Разрешает странице загружать iframe Turnstile. На страницах без внешних фреймов можно задать `'none'`. |
| `connect-src` | HTTPS нужен для Auth, REST, RPC и Edge Functions, WSS — для Realtime. Если сайт делает `fetch` на свой origin, добавьте `'self'`. |
| `form-action 'self'` | Ограничивает отправку HTML-форм своим origin. Запросы через `fetch` регулирует `connect-src`. |
| `upgrade-insecure-requests` | Переводит небезопасные URL ресурсов на HTTPS. Если источник не обслуживает HTTPS, загрузка всё равно упадёт. |

Фолбэк `default-src` не задаёт `base-uri`, `frame-ancestors` и `form-action`.
Для ужесточения CSS вынесите `<style>` в файлы, замените `style=` классами и
проверьте карту, всплывающие окна и анимации. Присваивание отдельных свойств
через `element.style` и установка атрибута `style` целиком ведут себя по-разному.
[Спецификация CSP](https://w3c.github.io/webappsec-csp/)

Turnstile требует `https://challenges.cloudflare.com` и в `script-src`, и в
`frame-src`. В режиме pre-clearance добавьте `'self'` в `connect-src` для
запроса на `/cdn-cgi/`. Серверная проверка токена из `assets/turnstile-gate.ts`
выполняется в Edge Function. CSP страницы на этот запрос не влияет.
[Cloudflare Turnstile и CSP](https://developers.cloudflare.com/turnstile/reference/content-security-policy/)

## Перевод и выкатка

1. **Снимите исходный список.** Из корня скилла запустите:

   ```sh
   node scripts/csp_scan.mjs /path/to/site
   node scripts/csp_scan.mjs /path/to/site --json
   ```

   Код 1 означает блокирующие находки. Предупреждения по CDN разберите отдельно.
   Сканер эвристический и пропускает тесты и ряд выходных каталогов, включая
   `dist` при обходе. Если публикуется сборка, передайте её каталог явно.
   Вручную проверьте import map, динамически созданные скрипты и HTML из шаблонов.

2. **Вынесите исполняемые `<script>…</script>`.** Перенесите код по страницам
   в `admin.js`, `track.js` и т. п. Сохраните порядок загрузки. Например,
   в конце `<body>` сначала идут зависимости и конфиг, затем код страницы:

   ```html
   <script src="./config.js"></script>
   <script src="./admin.js"></script>
   ```

   Если переносите обычные скрипты в `<head>`, поставьте `defer` всем звеньям
   цепочки в нужном порядке. `async` порядка не гарантирует. При переходе на
   `type="module"` проверьте явные импорты и обращения к глобальным переменным.

3. **Уберите HTML-обработчики.** Проверьте страницы и строки, которые попадают в
   `innerHTML` или `insertAdjacentHTML`. В шаблоне замените `onclick` на
   `data-act` и `data-id`, а `onchange` — на `data-filter` и слушатель
   `change`. Вызов `setAttribute('onclick', '...')` создаёт тот же запрещённый
   атрибут. Функция, переданная в `addEventListener`, загружается из разрешённого JS.

4. **Делегируйте события на стабильном контейнере.** Кнопки внутри контейнера
   можно перерисовывать через `innerHTML`. Слушатель остаётся на самом
   контейнере, а `closest` находит кнопку и при клике по вложенной иконке.

   ```html
   <section id="orders">
     <article data-order>
       <button type="button" data-act="details" data-id="42">Подробнее</button>
       <p data-details hidden>Заказ принят</p>
     </article>
   </section>
   ```

   ```js
   // admin.js
   const orders = document.querySelector('#orders');
   orders.addEventListener('click', event => {
     const button = event.target instanceof Element
       ? event.target.closest('button[data-act="details"]')
       : null;
     if (!button || !orders.contains(button)) return;

     const details = button.closest('[data-order]')?.querySelector('[data-details]');
     if (details) details.hidden = !details.hidden;
   });
   ```

   Для нескольких действий используйте явные ветки по `dataset.act`. При
   запросе к RPC валидируйте `dataset.id` и проверяйте права на сервере.
   Для `error` на картинках нужна фаза захвата. Установите слушатель до
   первой отрисовки карточек:

   ```js
   document.addEventListener('error', event => {
     const image = event.target;
     if (!(image instanceof HTMLImageElement)) return;
     const media = image.parentElement;
     if (!media?.matches('.card-media')) return;
     media.classList.add('no-image'); // класс показывает заглушку
     image.remove();
   }, { capture: true });
   ```

5. **Замените `javascript:` и выполнение строк.** Для действий используйте
   `<button type="button">`, для навигации — обычный `href`. Проверьте URL,
   присваиваемые из данных, и разрешайте только нужные схемы и источники.
   Вместо `eval` для JSON используйте `JSON.parse`, вместо строкового таймера —
   `setTimeout(refresh, 1000)`. Если `new Function` вызывает зависимость,
   выберите сборку без компиляции строк или замените зависимость.

6. **Закрепите CDN и добавьте SRI.** Для каждого стороннего JS/CSS с
   фиксированным содержимым выполните шаги из раздела ниже и снова запустите
   сканер. Сверьте также динамические загрузчики с `script-src`.

7. **Включите наблюдение.** В preview отдавайте целевую политику в заголовке
   `Content-Security-Policy-Report-Only`. Если уже есть блокирующая политика,
   оставьте её отдельным заголовком. Пройдите все страницы и сценарии.
   Для сбора отчётов настраивайте `Reporting-Endpoints` и `report-to` только
   при наличии приёмника. Проверьте, какие URL и фрагменты данных попадают в
   отчёты, прежде чем включать сбор на страницах с токенами.

8. **Включите блокировку.** Проверьте целевую CSP в режиме
   `Content-Security-Policy` на preview. Выкатывайте заголовки вместе с HTML,
   внешними JS и актуальными SRI-хэшами. После переключения проверьте
   боевые заголовки и сценарии. При регрессии возвращайте весь согласованный
   деплой, включая политику.

## CDN и SRI

Фиксируйте полную версию в URL файла и ограничивайте источник каталогом версии
в CSP, например `https://cdn.jsdelivr.net/npm/pkg@1.2.3/`. Завершающий `/`
задаёт префикс пути. Разрешение по пути сужает область на CDN, а SRI проверяет
байты конкретного файла. При HTTP-редиректе проверка пути CSP на следующем
переходе ослабляется. Используйте конечный URL без редиректа.

Из корня скилла получите атрибуты для каждого точного URL:

```sh
sh scripts/sri.sh \
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js' \
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
```

```html
<link rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H"
      crossorigin="anonymous">
<script defer
        src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH"
        crossorigin="anonymous"></script>
```

Скрипт печатает SHA-384. Убедитесь, что скачивание прошло успешно. Ошибка
`curl` в конвейере может оставить хэш пустого ввода. Для SRI на другом
origin нужен CORS-ответ CDN с `Access-Control-Allow-Origin` и
`crossorigin="anonymous"` в теге. Хэш проверяет сам ресурс, а его импорты,
шрифты и изображения требуют отдельных правил загрузки. При обновлении
меняйте URL, путь в CSP и SRI одновременно на всех страницах.
[Спецификация SRI](https://w3c.github.io/webappsec-subresource-integrity/)

Turnstile загружайте с официального URL. Его SDK обновляется у провайдера,
поэтому фиксированный хэш сломает загрузку при обновлении. CSS Google Fonts
может различаться по User-Agent. Если нужны фиксированные байты, разместите
CSS и файлы шрифтов у себя.
[Загрузка SDK Turnstile](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/)

## Остальные заголовки

- **HSTS** заставляет браузер обращаться к домену по HTTPS после первого
  получения заголовка по HTTPS. Добавляйте `includeSubDomains` после проверки
  HTTPS на поддоменах. `preload` требует отдельного решения и подачи домена
  в список браузеров.
- **X-Frame-Options: DENY** дублирует запрет встраивания для старых браузеров.
  Держите согласованным с `frame-ancestors`.
- **X-Content-Type-Options: nosniff** требует корректных MIME для JS и CSS.
  Проверьте, что запрос скрипта не получает HTML из запасного маршрута.
- **Referrer-Policy: strict-origin-when-cross-origin** оставляет только origin
  при HTTPS-переходах на другой origin. На страницах с токенами используйте
  `no-referrer` и `Cache-Control: no-store`, включая алиасы и чистые URL.
  Если поток допускает `/track.html#t=…`, фрагмент не отправляется в HTTP-запросе.
  Клиентский JS всё равно видит значение. Держите токены вне аналитики и отчётов.
- **Permissions-Policy** отключает ненужные API. `geolocation=(self)` подходит
  странице с геопозицией, `geolocation=()` — странице без неё.

## Грабли

- Обработчики `onclick` жили в шаблонах карточек, которые появляются после
  загрузки данных. Поиск только по статической разметке их пропускает. Откройте панель, дождитесь данных, обновите список и нажмите на
  вложенный элемент кнопки. Привязывайте делегирование к контейнеру,
  который переживает перерисовку.
- Резервная картинка задавалась через `onerror` в строке шаблона. Под
  строгой CSP такой обработчик не покажет заглушку. Обычное всплытие здесь не помогает,
  поскольку `error` на изображении не всплывает.
- Зависимость появлялась через `document.createElement('script')`. Проверка
  одних HTML-тегов пропускала загрузчик. Ищите присваивания `src`,
  `import()` и ветки ленивой загрузки.
- Ссылка трекинга содержала токен в query. Переход на фрагмент убрал его
  из HTTP-запросов страницы. Сохраняйте отдельные `no-store` и `no-referrer`
  и проверяйте каждый публичный URL страницы.

## Как проверить

1. **Локально.** Запустите `node tests/serve.mjs 8780`, если проект уже
   содержит такой сервер. Для своего сервера используйте тот же принцип.
   Прочитайте `vercel.json`, примените подходящие правила к URL запроса
   и отдайте файл с правильным `Content-Type`. Для локального HTTP
   уберите HSTS и `upgrade-insecure-requests` из локального ответа.
   Применяйте правила к URL до подстановки `index.html` и проверяйте
   переопределения на конкретном маршруте. Для правил из примера:

   ```js
   import { readFileSync } from 'node:fs';

   const { headers: rules } = JSON.parse(readFileSync('vercel.json', 'utf8'));
   function headersFor(pathname) {
     const headers = {};
     for (const rule of rules) {
       if (rule.source !== '/(.*)' && rule.source !== pathname) continue;
       for (const { key, value } of rule.headers) headers[key.toLowerCase()] = value;
     }
     delete headers['strict-transport-security'];
     for (const name of ['content-security-policy', 'content-security-policy-report-only']) {
       if (headers[name]) {
         headers[name] = headers[name].split(';')
           .filter(part => part.trim() !== 'upgrade-insecure-requests').join(';');
       }
     }
     return headers;
   }
   // Передайте результат headersFor(url.pathname) в res.writeHead вместе с MIME.
   ```

   ```sh
   curl -fsS -D - -o /dev/null http://127.0.0.1:8780/
   curl -fsS -D - -o /dev/null http://127.0.0.1:8780/track.html
   curl -fsS -D - -o /dev/null http://127.0.0.1:8780/admin.js
   ```

2. **В браузере под блокирующей CSP.** Откройте Console и Network, отключите
   кэш и перезагрузите страницу. Проверьте вход и MFA, кнопки после
   перерисовки, смену фильтра, ошибку загрузки фото, карту и её иконки,
   шрифты, Turnstile, запрос к RPC или Edge Function и WSS Realtime.
   Для тестов с Playwright подключите слушатель `securitypolicyviolation`
   через `page.addInitScript` до навигации. Сохраняйте `effectiveDirective`
   и `blockedURI`. На локальной копии временно добавьте тестовый inline
   `<script>` и кнопку с `onclick`, которые меняют текст страницы.
   Под блокирующей политикой текст не должен меняться. Аналогично временно
   подставьте неверный SRI-хэш и проверьте ошибку целостности в Console.

3. **На Vercel.** Проверьте реальный HTTPS-ответ, конечный URL после
   редиректов, алиасы и страницы с токеном без настоящего токена в URL.
   Локальный сервер воспроизводит простые правила, а маршрутизацию и
   заголовки CDN проверяйте по фактическому ответу.

   ```sh
   curl -fsS -D - -o /dev/null https://my-site.vercel.app/
   curl -fsS -D - -o /dev/null https://my-site.vercel.app/track.html
   ```

4. **Внешняя проверка.** При разрешении на внешний запрос проверьте публичный
   URL без токена через [Security Headers](https://securityheaders.com/).
   В [CSP Evaluator](https://csp-evaluator.withgoogle.com/) проверяйте строку
   политики. Он может отметить разрешённые CDN или `'self'`, поскольку
   доверенные источники тоже могут отдавать исполняемый контент. Устраняйте
   лишние разрешения и подтверждайте работу сценариев в браузере.
