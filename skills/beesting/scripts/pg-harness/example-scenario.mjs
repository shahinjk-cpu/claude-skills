// Пример сценария для harness.mjs. Скопируйте рядом с проектом и замените таблицы/функции на свои.
// Запуск: node harness.mjs --repo <проект> --scenario ./checks.mjs
//
// h.q(sql, params)                 — от postgres (суперпользователь, для подготовки данных)
// h.asAnon(sql, params)            — как сайт без входа (anon key)
// h.asUser(uid, sql, params, claims) — как вошедший пользователь; claims по умолчанию { aal: 'aal1' }
// h.asService(sql, params)         — как Edge Function с service_role
// h.createUser({ email, phone })   — строка в auth.users, возвращает uuid
// h.rejects(promise, /regex/)      — ожидать ошибку
// h.assert                         — node:assert/strict
export default async function (h) {
  // 1) Аноним не читает чужие заказы напрямую. В Supabase у anon есть GRANT на таблицы public,
  //    поэтому RLS обычно даёт «0 строк», а не ошибку. «permission denied» будет, только если права отозваны.
  const seen = await h.asAnon('select count(*)::int n from public.orders');
  h.assert.equal(seen.rows[0].n, 0, 'anon видит заказы');
  h.log('orders не видна anon');

  // 2) Заказ через RPC: цену считает сервер, а не клиент
  const menu = (await h.q(`select id, price from public.menu_items where available limit 1`)).rows[0];
  const r = await h.asAnon('select * from public.place_order($1::jsonb)', [JSON.stringify({
    phone: '+7 700 000 0001', name: 'Тест', address: 'ул. 1',
    items: [{ id: menu.id, qty: 2, price: 1 }], // подделанная цена должна игнорироваться
  })]);
  const row = (await h.q('select total from public.orders where id = $1', [r.rows[0].id])).rows[0];
  h.assert.equal(Number(row.total), Number(menu.price) * 2, 'сервер принял цену от клиента');
  h.log('итог считает сервер');

  // 3) Повтор с тем же client_key не создаёт второй заказ (идемпотентность)
  // 4) Лимит частоты: 4-й заказ с номера за 10 минут — отказ
  // 5) Персонал без 2FA (aal1) не видит заказы, с aal2 — видит
  const staff = await h.createUser({ email: 'op@example.com' });
  await h.q(`insert into public.staff (id, name, role) values ($1, 'Оператор', 'operator')`, [staff]);
  const aal1 = await h.asUser(staff, 'select count(*)::int n from public.orders');
  const aal2 = await h.asUser(staff, 'select count(*)::int n from public.orders', [], { aal: 'aal2' });
  h.assert.equal(aal1.rows[0].n, 0, 'без кода 2FA данные видны');
  h.assert.ok(aal2.rows[0].n > 0);
  h.log('заказы видны персоналу только после 2FA');
}
