# 2FA персонала через Supabase MFA

После входа паролем JWT имеет уровень `aal1`. После подтверждения TOTP
Supabase выдаёт сессии JWT с `aal2`. Экран кода управляет входом в панель.
Доступ к данным проверяют RLS и RPC по подписанному JWT: браузер может
отправлять запросы к API напрямую, минуя интерфейс. `aal2` подтверждает уровень
входа; роль сотрудника по-прежнему берётся из таблицы `staff`.
[Supabase MFA](https://supabase.com/docs/guides/auth/auth-mfa)

## Проверка в базе

Сведите проверки персонала к `public.is_staff(auth.uid())` и
`public.is_admin(auth.uid())`. Проверьте политики с альтернативными условиями
доступа, RPC с `SECURITY DEFINER`, аналитические view и доступ к данным через
Realtime. Прямые проверки членства, оставшиеся в отдельных RPC или политиках,
могут пропускать `aal1`. Для инвентаризации используйте
`references/supabase-audit.md`.

Пример новой миграции для существующей таблицы `public.staff(id, role)`.
Сохраните имена параметров, владельцев функций и действующие правила ролей
проекта. `uid = auth.uid()` позволяет проверять только себя.
`coalesce` отклоняет JWT без `aal`.

```sql
begin;

create or replace function public.is_staff(uid uuid)
returns boolean
language sql stable security definer
set search_path = public, pg_temp
as $$
  select uid is not null and uid = auth.uid()
     and coalesce(auth.jwt() ->> 'aal', '') = 'aal2'
     and exists (select 1 from public.staff where id = uid);
$$;

create or replace function public.is_admin(uid uuid)
returns boolean
language sql stable security definer
set search_path = public, pg_temp
as $$
  select uid is not null and uid = auth.uid()
     and coalesce(auth.jwt() ->> 'aal', '') = 'aal2'
     and exists (
       select 1 from public.staff where id = uid and role in ('admin', 'owner')
     );
$$;

revoke execute on function public.is_staff(uuid) from public, anon;
grant execute on function public.is_staff(uuid) to authenticated;
revoke execute on function public.is_admin(uuid) from public, anon, authenticated;

commit;
```

В этом варианте RLS вызывает `is_staff` от `authenticated`, а `is_admin`
вызывается внутри привилегированной RPC или view с подходящими правами
владельца. Если `is_admin` нужна непосредственно в RLS или
`security_invoker` view, вызывающей роли понадобится `EXECUTE`.
В PL/pgSQL используйте проверку `if public.is_admin(auth.uid()) is not true
then raise exception 'not admin'; end if;`: при неопределённом результате
доступ также закрыт.

## Панель на vanilla JS

Скопируйте `assets/staff-mfa.js` в сайт и загрузите перед скриптом панели.
Используйте тот же экземпляр Supabase JS v2 для входа, MFA, запросов к данным
и подписок. Задайте `issuer` как постоянную строку конфигурации приложения.

```html
<section id="mfa" class="hide"><div class="card"></div></section>
<script defer src="/staff-mfa.js"></script>
<script defer src="/admin.js"></script>
```

К этому моменту загрузите Supabase JS и определите класс `.hide`.
В `boot()` после проверки сессии и перед запросами к данным вставьте:

```js
async function confirmStaffSession(sb, signOutStaff) {
  const { data: { session }, error } = await sb.auth.getSession();
  if (error || !session) return false;
  return window.StaffMFA.ensure(sb, document.querySelector("#mfa"), {
    onSignOut: signOutStaff,
    issuer: "Панель персонала",
  });
}

// В async boot() панели:
// if (!(await confirmStaffSession(sb, signOutStaff)) || signingOut) return;
```

До завершения `ensure` держите рабочую панель скрытой. Если нужен ранний
поиск сотрудника по `session.user.id`, оставьте чтение собственной минимальной
записи под отдельной self-only политикой. Если поиск опирается на
`is_staff`, перенесите его после MFA: при `aal1` проверка вернёт отказ и
до экрана кода дело не дойдёт. После `ensure` загрузите роль, данные и
подписки. При выходе остановите таймеры, снимите подписки, очистите данные
панели и вызовите `sb.auth.signOut()`.

Что делает шаблон:

1. `getAuthenticatorAssuranceLevel()` возвращает `currentLevel` и
   `nextLevel`. Если текущий уровень уже `aal2`, можно продолжать.
   `nextLevel === 'aal2'` означает, что уровень можно повысить.
2. При `aal1` вызовите `listFactors()`. Для подтверждённого TOTP из
   `factors.totp` покажите ввод шестизначного кода.
3. Если подтверждённого TOTP нет, возьмите из `factors.all` незавершённые
   TOTP и удалите через `unenroll({ factorId })`. При адаптации шаблона
   обрабатывайте ошибку удаления до `enroll`. Затем вызовите
   `enroll({ factorType: 'totp', issuer, friendlyName })`, покажите
   `data.totp.qr_code` или ручной секрет. QR и секрет не храните в логах
   и очищайте из интерфейса при завершении или выходе.
4. `challengeAndVerify({ factorId, code })` создаёт challenge и проверяет
   код. После успеха SDK использует обновлённую сессию. Если вызываете API
   через свой `fetch`, возьмите новый access token. При неверном или
   просроченном коде оставьте возможность повтора без новой привязки,
   при rate limit покажите, что нужно подождать.

## Выкатка

1. **Проверить настройки Auth.** Включите TOTP enrollment и verification.
   Для паролей персонала настройте минимум 12 символов и проверьте действующие
   учётные записи. Сохраните ограничения попыток входа и MFA verification.
   Если саморегистрация не нужна витрине и другим клиентам, отключите
   `Allow new users to sign up`. Учётные записи персонала создавайте
   административно. [Настройки Auth](https://supabase.com/docs/guides/auth/general-configuration)
2. **Выкатить сайт.** Обновите все панели персонала. Проверьте привязку,
   повторный вход и выход, а также восстановление после неверного кода.
   На этом этапе прежние правила базы ещё действуют.
3. **Дождаться всех сотрудников.** Каждый администратор и оператор
   привязывает фактор и входит по коду в новой сессии. Перед переключением
   проверьте наличие подтверждённого фактора у каждого. Начальную привязку
   и повторную привязку после сброса проводите после подтверждения личности:
   у аккаунта без фактора пароль позволяет начать enrollment.
4. **Применить миграцию.** Прогоните её на стенде и примените последней.
   Проверьте, что с `aal1` защищённые данные и операции недоступны, с
   `aal2` оператор видит свои разделы, а администратор выполняет свои
   операции. Публичные сценарии сайта должны продолжать работать.

## Сброс фактора

Подтвердите личность сотрудника и найдите точный UUID в Authentication →
Users. Удалите нужный фактор через Auth Admin API из доверенного серверного
окружения. Здесь `adminClient` — экземпляр клиента с серверным ключом,
`userId` и `factorId` — проверенные UUID.

```js
const { error } = await adminClient.auth.admin.mfa.deleteFactor({
  userId,
  id: factorId,
});
if (error) throw error;
```

Supabase завершает активные сессии при удалении подтверждённого фактора.
Уже выпущенный access token может оставаться действительным до истечения
срока, если приложение проверяет только JWT. Попросите сотрудника заново
войти. При отсутствии подтверждённых факторов откроется привязка телефона.
Удаление строк напрямую из `auth.mfa_factors` встречается в старых
инструкциях; используйте Auth Admin API для штатного сброса с завершением
сессий. [Supabase deleteFactor](https://supabase.com/docs/reference/javascript/auth-admin-deletefactor)

## Откат

Подготовьте новый SQL-файл с предыдущими определениями `is_staff` и
`is_admin` и прежними грантами. Восстановите их одной транзакцией, сохранив
ограничение на свой UID и проверку роли. Проверьте панели. Если нужен откат
фронта, делайте его после SQL: старый клиент иначе остановится на `aal1`.
Уже привязанные факторы сохраняются. После SQL-отката пароль снова достаточен
для запросов к данным персонала, даже если панель по-прежнему просит код.

## Грабли

- Брошенная привязка оставляла неподтверждённый TOTP, который мешал следующей
  попытке. Чистите только незавершённые TOTP. Блокируйте повторный запуск
  `boot()` и двойную отправку кода, пока проверка в процессе.
- Если включить SQL до обновления панелей и привязки, старые сессии останутся
  на `aal1`. RLS на чтении может вернуть пустой список без ошибки, поэтому
  проверяйте доступ на заранее созданной записи.
- Если переиспользовать JWT, захваченный до MFA, запросы будут идти с
  `aal1` даже после верного кода. Запускайте загрузку и Realtime после MFA
  и пересоздавайте старые подписки.
- Строгая CSP может скрыть QR: ассет получает `data:image/svg+xml`. Проверьте
  `img-src` и ручную привязку по ключу. Если действующая политика блокирует
  inline-стили, перенесите стили шаблона во внешний CSS.
- В шаблоне выход из формы вызывает `onSignOut`. Если интеграция не
  перезагружает страницу, при адаптации завершайте ожидающий `ensure`
  с `false`, чтобы следующий вход мог начать новый цикл.

## Как проверить

В сценарии для `scripts/pg-harness/` ниже используются `public.staff(id, name,
role)` и RLS на `public.orders`. Подготовьте одну запись заказа, которую
оператор должен видеть. Если есть публичная политика чтения, выбирайте
заказ или операцию, защищённые именно проверкой персонала.

```js
export default async function (h) {
  const operator = await h.createUser({ email: "operator@example.com" });
  const outsider = await h.createUser({ email: "outsider@example.com" });
  await h.q(
    "insert into public.staff (id, name, role) values ($1, 'Оператор', 'operator')",
    [operator],
  );
  const sql = "select count(*)::int as n from public.orders";
  const aal1 = await h.asUser(operator, sql, [], { aal: "aal1" });
  const aal2 = await h.asUser(operator, sql, [], { aal: "aal2" });
  const nonStaff = await h.asUser(outsider, sql, [], { aal: "aal2" });
  h.assert.equal(aal1.rows[0].n, 0);
  h.assert.ok(aal2.rows[0].n > 0);
  h.assert.equal(nonStaff.rows[0].n, 0);
}
```

Добавьте проверки проекта на админскую RPC: оператор с `aal2` и
администратор с `aal1` получают отказ, администратор с `aal2` выполняет
операцию. Проверяйте фактический результат через публичную точку вызова.

```bash
node "$HARNESS/harness.mjs" --repo "$PROJECT" --scenario "$CHECKS" --twice staff_mfa.sql
```

`HARNESS` — копия `scripts/pg-harness/` после `sh setup.sh`, `PROJECT` —
каталог проекта, `CHECKS` — путь к сценарию с подготовкой данных и проверками.
Подставьте имя миграции. Стенд имитирует claims PostgREST. Отдельно в браузере
проверьте первый вход с QR, повторный вход с кодом, отказ при неверном коде,
выход, сброс фактора и повторную привязку.
