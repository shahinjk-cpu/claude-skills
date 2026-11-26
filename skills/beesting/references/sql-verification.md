# Проверка SQL-миграций перед передачей владельцу

Владелец применяет SQL вручную в Supabase SQL Editor. Ошибка в порядке файлов, сигнатуре RPC
или грантах может остановить запись с сайта или оставить данные доступными лишней роли.
Прогоните всю цепочку на чистой временной базе и отдельно проверьте, что новый файл
безопасно применить повторно после сбоя или повторного запуска из SQL Editor.

## Что проверяет стенд

`scripts/pg-harness/harness.mjs` запускает встроенный Postgres 17. Каждый запуск поднимает
новую базу, применяет SQL от `postgres`, печатает аудит и запускает сценарий, если он задан.

- Роли `anon`, `authenticated`, `service_role` без логина. У `service_role` есть
  `BYPASSRLS`, но ей по-прежнему нужны гранты.
- `auth.uid()`, `auth.role()`, `auth.jwt()` и `auth.email()` читают настройки сессии
  `request.jwt.claims`, `request.jwt.claim.sub` и `request.jwt.claim.role`. Таблицы
  `auth.users` и `auth.mfa_factors` содержат минимальный набор полей для фикстур и FK.
- Default privileges по модели Supabase для объектов, создаваемых `postgres` в `public`.
  Три роли получают права на новые таблицы и последовательности и `EXECUTE` на функции.
  Фактические ACL проекта могут отличаться, особенно если менялись владелец или default privileges.
- Есть пустая публикация `supabase_realtime`. Стенд пытается установить `pgcrypto`,
  `uuid-ossp`, `citext` и `pg_trgm` в схему `extensions`; недоступные в сборке
  расширения пропускаются. Схема `extensions` входит в начальный `search_path`.

Модель заканчивается на SQL. Подстановка claims не проверяет подпись JWT, выдачу токена или
TOTP. HTTP-маршрутизация PostgREST, выбор перегрузки RPC, кэш схемы, Storage, доставка
Realtime-событий и вызовы Edge Functions проверяются отдельно в тестовом Supabase-проекте.
Локальный успешный прогон также оставляет открытым вопрос совместимости с уже накопленными
данными и фактическими правами роли владельца в SQL Editor.

### Если миграция зависит от pg_net, pg_cron или Vault

Подготовьте во временной копии миграций первый файл `bootstrap-local.sql`. Создайте
только схемы, колонки и сигнатуры, которые использует SQL, включая имена аргументов
для вызовов с `:=`. Если в цепочке есть `CREATE EXTENSION` для отсутствующего
расширения, подмените эту строку заглушкой только в тестовой копии и зафиксируйте
отличие в отчёте. Заглушка не регистрирует расширение в `pg_extension`.
Пример для вызовов с `net.http_post`, `cron.schedule` и чтением Vault.
[Пример вызовов в Supabase Docs](https://supabase.com/docs/guides/functions/schedule-functions)

```sql
-- bootstrap-local.sql, только для временного стенда
create schema net;
create schema cron;
create schema vault;

create function net.http_post(
  url text,
  body jsonb default '{}'::jsonb,
  params jsonb default '{}'::jsonb,
  headers jsonb default '{"Content-Type":"application/json"}'::jsonb,
  timeout_milliseconds integer default 2000
) returns bigint language sql as $$ select 1::bigint $$;

create function cron.schedule(job_name text, schedule text, command text)
returns bigint language sql as $$ select 1::bigint $$;

create view vault.decrypted_secrets as
select 'api_key'::text as name, 'local-test-only'::text as decrypted_secret;
```

Добавьте `bootstrap-local.sql` первым в `--migrations`. Для тестов вызова из прикладной
роли воспроизведите нужные гранты адресно. Фиктивный ID подтверждает связность SQL.
Чтобы проверить параметры вызова, пишите их в локальную таблицу и сверяйте из сценария.
Отправку HTTP, выполнение задания по расписанию и управление секретами проверьте отдельно.

## Как проверить

1. Из корня скилла скопируйте стенд во временный каталог. Для установки нужны Node.js и npm.
   `node_modules` останется во временной копии.

   ```sh
   work=$(mktemp -d)
   cp -R scripts/pg-harness "$work/pg-harness"
   cd "$work/pg-harness"
   sh setup.sh
   ```

2. Примените предыдущие миграции в порядке выкатки, затем новый файл. Во второй
   команде замените имена файлов и положите `checks.mjs` во временную копию стенда.

   ```sh
   repo=/path/to/my-site
   node harness.mjs --repo "$repo" --twice supabase_bugfixes.sql
   node harness.mjs --repo "$repo" \
     --migrations supabase.sql,supabase_hardening.sql,supabase_bugfixes.sql \
     --twice supabase_bugfixes.sql --scenario ./checks.mjs --json ./report.json
   ```

   Сверьте строки `✓ применён` с инструкцией владельцу. При выкатке в несколько этапов
   прогоните также промежуточные состояния с соответствующим списком файлов.
   Если миграция меняет формат данных, проверьте её и на строках старого формата.
   Подготовительный SQL с фикстурами можно вставить в локальный список непосредственно
   перед новым файлом. Сценарий запускается уже после миграций.

3. Разберите аудит и результат сценария. Код выхода `0` означает, что миграции и
   заданный сценарий прошли. Предупреждения аудита не меняют код выхода. При ошибке
   миграции стенд останавливается с кодом `1` и печатает файл и, если сервер сообщил
   позицию, строку. Сокращённый вывод прогона с повтором и сценарием

   ```text
   ✓ применён supabase_bugfixes.sql
   ✓ применён supabase_staff_mfa.sql
   ✓ повторно применён supabase_bugfixes.sql
   ✓ Таблицы public без RLS: нет
   ⚠ Политики «true» для public/anon/authenticated: 1
      - menu_items.menu_public_read [SELECT {anon,authenticated}] using=true check=-
   ✓ SECURITY DEFINER без set search_path: нет
   ⚠ Функции, доступные через /rest/v1/rpc (проверить каждую): 25
   ── Сценарий ./checks.mjs
   ✓ anon без EXECUTE на place_order
   ✓ повтор с тем же ключом оставил один заказ
   ✓ is_staff требует членство и aal2
   СЦЕНАРИЙ ПРОЙДЕН
   ```

### Флаги

| Флаг | Действие |
| --- | --- |
| `--repo DIR` | Корень проекта. По умолчанию текущий каталог. |
| `--migrations a.sql,b.sql` | Явный порядок. Пути относительно `--repo`. Без флага берётся первый подходящий документ из `DEPLOY.md`, `README.md`, `MIGRATIONS.md`, `docs/*.md`. Парсер ищет строки вида `1. a.sql` или `2) b.sql`, включая имена в бэктиках. Условия из текста он не исполняет. |
| `--twice x.sql,y.sql` | Выполняет перечисленные файлы ещё раз после основной цепочки. Для настоящего повтора включите их и в основную цепочку. |
| `--scenario ./checks.mjs` | Загружает модуль из пути относительно текущего каталога. Вызовет экспорт `default` либо `run`. |
| `--no-audit` | Пропускает аудит. Удобно для отладки сценария. |
| `--json ./report.json` | Записывает результаты миграций, аудита и сценария. Файл создаётся после подключения к базе и выполнения проверок; сбой запуска может оставить без отчёта. |
| `--port 54330` | Порт локального Postgres. По умолчанию `54329`. |

### Как читать аудит

| Строка отчёта | Что проверить |
| --- | --- |
| Таблицы `public` без RLS | Клиентские гранты на закрытые данные требуют исправления. Для внутренней таблицы с отозванными правами подтвердите отказ и для `anon`, и для `authenticated`. |
| Политики `true` | Открытый `SELECT` на публичном справочнике допустим. Безусловная запись требует обоснования и проверки вместе с эффективными грантами. Поиск ловит буквальное `true`, поэтому сложные условия проверяйте сценариями. |
| `SECURITY DEFINER` без `search_path` | Зафиксируйте путь, например `set search_path = public, pg_temp`, если вызывающие роли не могут создавать объекты в `public`. Аудит видит наличие параметра, содержимое проверяйте вручную. |
| Доступные RPC | Сверьте `EXECUTE` каждой сигнатуры с контрактом. Метка «через PUBLIC» требует проверки ACL. «Без проверки личности» определяется поиском по телу функции. Публичный RPC по токену может быть штатным, если проверяет токен и возвращает только нужные данные. |
| Читаемые view без `security_invoker` | Обычное view использует права владельца для доступа к базовым таблицам. Для обычного view проверьте `security_invoker = true` или отзовите клиентский `SELECT`. Для materialized view проверяйте доступ к сохранённым строкам и гранты. |
| Прямая запись `anon` | Это кандидаты по сочетанию ACL и политик. Проверьте нужную операцию и ожидаемое состояние строки после неё. Запись через RPC сама по себе не закрывает прямую запись. |
| `supabase_realtime` | Список таблиц в публикации. Сверьте его с намерением и проверьте SELECT-политики. |

Детали по правам и RLS см. в `references/supabase-audit.md`.

## Как писать сценарии

Возьмите за основу `scripts/pg-harness/example-scenario.mjs`. Запросы запускайте
последовательно через `await`: одна сессия переключает роль и claims. Через `h.q`
готовьте фикстуры и проверяйте фактическое состояние базы от `postgres`, а доступ
проверяйте через `h.asAnon`, `h.asUser` или `h.asService`.

**RLS и гранты.** Для таблицы с правом `SELECT` и политикой владельца сначала
подтвердите, что владелец видит конкретную строку, затем проверьте, что другой
пользователь получает `rowCount === 0` на том же запросе. Пустая таблица даёт ложный
успех отрицательной проверки. Если грант должен быть отозван, ожидайте SQLSTATE
`42501` через `h.rejects`. Для бизнес-отказа проверяйте конкретную ошибку, например
`/not staff/`, или явный результат `false` / пустой набор по контракту функции.

**2FA.** Создайте пользователя через `h.createUser` до вставки связанной строки.
Один и тот же сотрудник должен получить отказ с `aal1` и доступ с `aal2`. Проверьте
также постороннего пользователя с `aal2`. Ниже пример для схемы со `staff(id, name, role)`
и `is_staff(uuid)`.

```js
export default async function (h) {
  const uid = await h.createUser({ email: 'staff@example.test' });
  const other = await h.createUser();
  await h.q(
    'insert into public.staff (id, name, role) values ($1, $2, $3)',
    [uid, 'Тест', 'admin'],
  );

  const sql = 'select public.is_staff($1::uuid) as ok';
  await h.rejects(h.asAnon(sql, [uid]), { code: '42501' });
  h.assert.equal((await h.asUser(uid, sql, [uid])).rows[0].ok, false);
  h.assert.equal((await h.asUser(uid, sql, [uid], { aal: 'aal2' })).rows[0].ok, true);
  h.assert.equal((await h.asUser(other, sql, [other], { aal: 'aal2' })).rows[0].ok, false);
  h.log('is_staff требует членство и aal2');
}
```

**Идемпотентность RPC.** Отдельно от `--twice` вызовите RPC дважды с тем же ключом
и валидным payload. В примере `payload` содержит данные тестового заказа и
`clientKey` — UUID. Если запись идёт через Edge-шлюз, используйте `h.asService`
для SQL-вызова, а отказ для `anon` проверьте отдельно.

```js
const sql = 'select * from public.place_order($1::jsonb)';
const args = [JSON.stringify({ ...payload, client_key: clientKey })];
await h.rejects(h.asAnon(sql, args), { code: '42501' });
const first = (await h.asService(sql, args)).rows[0];
const repeat = (await h.asService(sql, args)).rows[0];
h.assert.ok(first.order_no);
h.assert.equal(repeat.order_no, first.order_no);
const { rows: [count] } = await h.q(
  'select count(*)::int n from public.orders where client_key = $1',
  [clientKey],
);
h.assert.equal(count.n, 1);
```

**Окна частоты.** Чтобы предыдущие фикстуры не исчерпали лимит в следующем
тесте, состарьте их от `postgres`. Ограничьте UPDATE идентификаторами созданных
строк. В отдельной проверке лимита сохраните свежий `created_at`, проверьте отказ,
затем состарьте строки и проверьте, что новый запрос проходит.

```js
await h.q(
  "update public.orders set created_at = now() - interval '1 hour' where id = any($1::bigint[])",
  [fixtureOrderIds],
);
```

**Часовые пояса.** Сравните часы и минуты в зоне бизнес-правила, затем проверьте
интервал между двумя абсолютными моментами. Выберите время позже стандартного
ETA, чтобы проверить именно запланированную доставку. Добавьте случай с переходом
через местную полночь. Здесь `tz` — IANA-зона из проекта, `expectedHm` — переданное
RPC местное время, `order` — результат вызова.

```js
const { rows: [eta] } = await h.q(
  `select to_char($1::timestamptz at time zone $3, 'HH24:MI') as hm,
          extract(epoch from ($1::timestamptz - $2::timestamptz)) / 60 as minutes`,
  [order.eta_delivery_at, order.eta_ready_at, tz],
);
h.assert.equal(eta.hm, expectedHm);
h.assert.equal(Number(eta.minutes), 20);
```

## Грабли

- **macOS и симлинки.** Если старт Postgres падает на загрузке библиотеки, повторите
  `sh setup.sh`. Скрипт запускает `scripts/hydrate-symlinks.js` из установленного
  пакета `@embedded-postgres` и скрывает его вывод. Для диагностики запустите этот
  JS вручную из каталога пакета внутри `node_modules/@embedded-postgres/`.
- **Порт занят.** Повторите запуск с `--port 54330` или другим свободным портом.
- **FK персонала.** Случайный UUID в `staff.id` падает на FK, если пользователя
  ещё нет в `auth.users`. Сначала `h.createUser()`, затем INSERT с его UUID.
- **Новый тип результата RPC.** `CREATE OR REPLACE FUNCTION` с теми же входными
  типами не меняет тип результата, в том числе форму `RETURNS TABLE`. Удалите
  прежнюю сигнатуру и пересоздайте функцию. Проверьте зависимости и в той же
  транзакции восстановите `REVOKE`/целевые `GRANT EXECUTE`. Новый объект получает
  default privileges, поэтому повтор сам по себе не гарантирует прежний ACL.
- **Изменились правила шлюза.** Старый сценарий вызывал `place_order` как `anon`.
  После переключения на Edge-шлюз тест успешного оформления должен идти через
  `service_role`, а вызов от `anon` должен получить `42501`. Повтор SQL не должен
  вернуть публичный `EXECUTE`.

## Перед передачей владельцу

1. Прогоните всю цепочку в порядке из инструкции владельцу, включая новый файл.
   Сверьте порядок с уже выкаченными изменениями и условиями включения шлюза или 2FA.
2. Повторно примените новый файл через `--twice`. Для обновления существующей базы
   проверьте также сохранение старых строк и заполнение новых полей.
3. Проверьте своего, чужого и анонимного пользователя. Для служебных RPC добавьте
   `service_role`, для персонала — сравнение `aal1` и `aal2`.
4. После каждого `DROP FUNCTION` сверяйте эффективный `EXECUTE` по точной сигнатуре,
   включая доступ через `PUBLIC`. Проверьте отказ и успешный вызов после повтора файла.
5. Передайте владельцу порядок выполнения в SQL Editor, условия выкатки и короткие
   проверки сайта после применения. Если использовались заглушки, укажите, какие
   интеграции требуют проверки на тестовом проекте.
