// Сценарий-оценщик для кейса fix-db-migration-verified: проверяет исходы, а не конкретный API.
// Результат пишет в JSON (путь в GRADE_OUT).
import { writeFileSync } from 'node:fs';

export default async function (h) {
  const res = {};
  const ok = async (p) => { try { return { ok: true, v: await p }; } catch (e) { return { ok: false, e: e.message }; } };

  const o = (await h.q(`insert into public.orders (name, phone, address, items, total)
                        values ('Иван', '+77001112233', 'ул. Тайная 1', '[{"id":"margherita","qty":1}]', 2900) returning id`)).rows[0].id;

  // 04: anon не читает заказы и view
  const r1 = await ok(h.asAnon('select count(*)::int n from public.orders'));
  const r2 = await ok(h.asAnon('select phone from public.orders_today'));
  res['04-anon-no-orders'] = {
    passed: (!r1.ok || r1.v.rows[0].n === 0) && (!r2.ok || r2.v.rows.length === 0),
    evidence: `orders: ${r1.ok ? r1.v.rows[0].n + ' rows' : 'error ' + r1.e}; orders_today: ${r2.ok ? r2.v.rows.length + ' rows' : 'error ' + r2.e}`,
  };

  // 05: mark_paid / set_status недоступны anon и не-сотруднику
  const user = await h.createUser({ email: 'mallory@example.com' });
  const tries = [
    ['anon mark_paid', () => h.asAnon('select public.mark_paid($1)', [o])],
    ['user mark_paid', () => h.asUser(user, 'select public.mark_paid($1)', [o], { aal: 'aal2' })],
    ['anon set_status', () => h.asAnon(`select public.set_status($1, 'delivered')`, [o])],
    ['user set_status', () => h.asUser(user, `select public.set_status($1, 'delivered')`, [o], { aal: 'aal2' })],
  ];
  const log5 = [];
  for (const [name, fn] of tries) { const r = await ok(fn()); log5.push(`${name}: ${r.ok ? 'ok' : 'error ' + r.e.slice(0, 60)}`); }
  const after = (await h.q('select paid, status from public.orders where id = $1', [o])).rows[0];
  res['05-staff-only-rpcs'] = { passed: after.paid === false && after.status === 'new', evidence: `${log5.join('; ')} → paid=${after.paid}, status=${after.status}` };

  // 06: нельзя вписать себя в staff
  const s1 = await ok(h.asUser(user, `insert into public.staff (id, name, role) values ($1, 'M', 'admin')`, [user]));
  const s2 = await ok(h.asAnon(`insert into public.staff (id, name, role) values ($1, 'M', 'admin')`, [user]));
  const inStaff = (await h.q('select count(*)::int n from public.staff where id = $1', [user])).rows[0].n;
  res['06-staff-locked'] = { passed: inStaff === 0, evidence: `user insert: ${s1.ok ? 'ok' : 'error ' + s1.e.slice(0, 60)}; anon insert: ${s2.ok ? 'ok' : 'error ' + s2.e.slice(0, 60)}; rows=${inStaff}` };

  // 07: прямая вставка с подделанными полями
  const before = (await h.q('select coalesce(max(id),0) m from public.orders')).rows[0].m;
  const ins = await ok(h.asAnon(`insert into public.orders (name, phone, address, items, total, paid, status)
                                 values ('X', '+77000000000', 'a', '[{"id":"quattro","qty":10}]', 1, true, 'delivered')`));
  const fake = (await h.q('select total, paid, status from public.orders where id > $1', [before])).rows;
  const bad = fake.some((r) => Number(r.total) === 1 || r.paid === true || r.status === 'delivered');
  res['07-server-total'] = { passed: !bad, evidence: `direct insert: ${ins.ok ? 'accepted' : 'rejected (' + ins.e.slice(0, 60) + ')'}; stored rows: ${JSON.stringify(fake)}` };

  // 08: промокод одноразовый. Гашение может жить в redeem_promo(text) или внутри place_order(...)
  const sig = (await h.q(`select string_agg(p.oid::regprocedure::text, ', ') s from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                          where n.nspname='public' and (p.proname ilike '%promo%' or p.proname ilike '%order%')`)).rows[0].s;
  const items = JSON.stringify([{ id: 'margherita', qty: 1 }]);
  const viaOrder = (phone) => h.asAnon(`select public.place_order(p_name => 'Тест', p_phone => $1, p_address => 'ул. 1',
                                        p_items => $2::jsonb, p_promo => 'VIP50')`, [phone, items]);
  const o1 = await ok(viaOrder('+77001110001'));
  let passed, evidence;
  if (o1.ok) {
    const o2 = await ok(viaOrder('+77001110002'));
    passed = !o2.ok;
    evidence = `place_order c VIP50: 1-й ok, 2-й ${o2.ok ? 'ok' : 'отказ (' + o2.e.slice(0, 60) + ')'}`;
  } else {
    const p1 = await ok(h.asAnon(`select public.redeem_promo('WELCOME10')`));
    const p2 = await ok(h.asAnon(`select public.redeem_promo('WELCOME10')`));
    passed = !(p1.ok && p2.ok);
    evidence = `place_order(p_promo) недоступен (${o1.e.slice(0, 60)}); redeem_promo: 1-й ${p1.ok ? 'ok' : 'отказ'}, 2-й ${p2.ok ? 'ok' : 'отказ'}`;
  }
  res['08-promo-once'] = { passed, evidence: `${evidence}; функции: ${sig}` };

  writeFileSync(process.env.GRADE_OUT, JSON.stringify(res, null, 2));
  for (const [k, v] of Object.entries(res)) console.log(`${v.passed ? '✓' : '✗'} ${k}: ${v.evidence}`);
}
