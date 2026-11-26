# Аудит Supabase: что искать и как чинить

Модель угроз: anon key и URL проекта публичны, их видит любой в DevTools. Всё, что
разрешено роли `anon` (и `authenticated` после бесплатной регистрации), атакующий может
вызвать напрямую через `/rest/v1/...` и `/rest/v1/rpc/...` в обход сайта. Поэтому вся защита
живёт в базе: RLS, гранты и проверки внутри функций. Проверки на клиенте — только для UX.

## Содержание
1. Права на таблицы и RLS
2. Функции (RPC) и SECURITY DEFINER
3. View и realtime
4. Бизнес-логика: деньги, лимиты, идемпотентность
5. Клиентский код
6. Персонал: роли и 2FA
7. Шаблон миграции-исправления

## 1. Права на таблицы и RLS

В Supabase на всё, что создано в `public`, по умолчанию выданы права `anon`, `authenticated`,
`service_role` (default privileges). Значит:

- Таблица без `enable row level security` полностью открыта на чтение и запись.
- RLS включён, но нет политик: всё закрыто (это нормально для служебных таблиц).
- При RLS чужие строки дают «0 строк», а не ошибку. «permission denied» бывает только после `revoke`.
- Политика `using (true)` на SELECT подходит для публичного справочника (меню). На
  INSERT/UPDATE/DELETE для anon это почти всегда дыра.
- `with check` нужен у INSERT/UPDATE, иначе пользователь запишет строку «от чужого имени»
  (подменит `user_id`, `status`, `price`).
- Колонки: RLS работает построчно. Если anon должен видеть строку, но не телефон, нужен
  отдельный RPC или view с `security_invoker`, либо `revoke select (phone)`/грант по колонкам.

Служебная таблица, к которой ходят только функции:
```sql
alter table public.x enable row level security;
revoke all on public.x from public, anon, authenticated;
```

## 2. Функции (RPC) и SECURITY DEFINER

- `EXECUTE` на новые функции по умолчанию есть у роли `PUBLIC`. Одного `revoke ... from anon`
  мало: anon наследует от PUBLIC. Правильно так:
  ```sql
  revoke execute on function public.f(args) from public, anon, authenticated;
  grant  execute on function public.f(args) to authenticated;   -- кому реально нужно
  ```
  Сигнатура в `revoke/grant` должна точно совпадать с аргументами (`public.f(text, int)`).
- `security definer` выполняется с правами владельца (postgres) и обходит RLS. Каждой такой
  функции нужно `set search_path = public, pg_temp`, иначе подмена объектов через search_path.
- Внутри definer-функции проверяйте личность явно: `auth.uid()`, `public.is_staff(auth.uid())`,
  владение строкой (`where courier_id = auth.uid()`), секрет-токен (`where track_token = p_token`).
- Доступ по токену из ссылки: только `uuid`/случайный ≥128 бит, не порядковый номер заказа.
  Возвращайте минимум полей (без телефона/адреса, если трекинг публичен).
- Меняете тип возврата: `create or replace` не сработает, нужно `drop function ...; create function ...`
  и заново выдать гранты (они пропадают вместе с функцией).
- Ошибки: `raise exception 'too many orders'` — короткий машинный код, клиент сам переводит его в
  понятный текст. Не возвращайте наружу SQL-детали.

## 3. View и realtime

- View, созданная postgres, по умолчанию выполняется с правами владельца и обходит RLS.
  Postgres 15+: `alter view public.v set (security_invoker = true);` или отзовите select у anon.
- Realtime (`postgres_changes`) отдаёт строки по тем же SELECT-политикам. Таблица в публикации
  `supabase_realtime` с широкой SELECT-политикой выдаёт все изменения всем подписчикам.

## 4. Бизнес-логика: деньги, лимиты, идемпотентность

- Цена, скидка, итог, статус — только на сервере. Клиент присылает `id` и `qty`, функция
  берёт цены из таблицы, проверяет `available`, минимальную сумму, длину корзины (1–100 строк),
  `qty` (1–50), длины строк (имя, адрес, комментарий).
- Лимиты частоты внутри RPC: N заказов на номер за окно, общий потолок за окно.
  От гонок защищают advisory lock на ключ (`pg_advisory_xact_lock(<namespace>, hashtext(key))`)
  и счётчик по индексу (`created_at`, нормализованный телефон).
- Нормализуйте телефон одной функцией (`phone_key(text)` → только цифры, 8→7) и сравнивайте
  везде через неё: промокоды «на номер», лимиты, рефералки.
- Идемпотентность: клиент шлёт `client_key uuid`, частичный уникальный индекс плюс advisory lock.
  Повтор возвращает уже созданный заказ, а не второй (таймауты, двойной клик).
- Промокоды и призы: проверка и погашение в одной транзакции (`update ... where used = false
  returning`), привязка к телефону владельца, одноразовость, срок действия.
- Статусы: переходы только разрешённые (`new→accepted→...`), а роль проверяется на каждом шаге.

## 5. Клиентский код

- `service_role` ключ не должен попадать на клиент (grep `service_role`, `eyJ` с role service).
- Прямые `.from('orders').insert/update` с сайта переводите в RPC с валидацией.
- Запросы supabase-js ленивые: `sb.rpc(...)` / `sb.from(...).update(...)` без `await` или `.then()`
  не выполняются. Поиск: вызовы, результат которых не ожидается и не возвращается.
- Проверяйте `error` у каждого вызова, иначе сбой выглядит как «пусто».
- XSS: данные пользователей (имя, адрес, комментарий, отзыв) в `innerHTML` — только через
  экранирование (`esc()`), либо `textContent`. Особенно в панелях персонала: XSS там = захват сессии
  оператора.
- Персональные данные не кладите в URL (query, `wa.me?text=`, аналитика): они оседают в логах
  и Referer. Для страниц с токеном: `Referrer-Policy: no-referrer`, `Cache-Control: no-store`.
- Storage: публичные бакеты видны всем; загрузка — с политиками на `storage.objects`.

## 6. Персонал: роли и 2FA

- Одна функция-источник истины: `is_staff(uid)`, `is_admin(uid)` (definer, search_path), все
  политики и RPC персонала вызывают её. Тогда усиление (например 2FA) делается в одном месте.
- 2FA (TOTP через Supabase MFA): в `is_staff/is_admin` добавить
  `coalesce(auth.jwt() ->> 'aal', '') = 'aal2'`. Порядок выкатки — в `staff-mfa.md`.
- Регистрация открыта (Auth → Email signup): любой получает роль `authenticated`. Поэтому всё,
  что выдано `authenticated`, должно само проверять, что это сотрудник или владелец строки.

## 7. Шаблон миграции-исправления

Применённые миграции не редактируйте: владелец базы уже их выполнил. Новый файл применяется последним.

```sql
-- ============================================================================
--  <проект> — <что чиним, одной строкой>.
--  Применять после <последний файл>. Идемпотентен — можно запускать повторно.
--  Что меняется для сайта: <какие версии клиента совместимы, порядок выкатки>.
--  Откат: <команда или файл>.
-- ============================================================================
begin;

alter table public.orders add column if not exists client_key uuid;
create unique index if not exists orders_client_key_uidx on public.orders (client_key) where client_key is not null;

create or replace function public.f(p text)
returns ... language plpgsql security definer set search_path = public, pg_temp as $$
begin
  ...
end $$;

drop policy if exists "orders_staff_select" on public.orders;
create policy "orders_staff_select" on public.orders for select to authenticated
  using (public.is_staff(auth.uid()));

revoke execute on function public.f(text) from public, anon, authenticated;
grant  execute on function public.f(text) to anon;

commit;
```

Обязательно: прогон на стенде (`sql-verification.md`) со всеми предыдущими миграциями,
повторное применение файла и сценарии «чужой не может / свой может».
