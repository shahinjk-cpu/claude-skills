#!/usr/bin/env node
// Supabase-подобный Postgres 17 на локальной машине: применяет миграции проекта по порядку,
// печатает аудит прав (RLS, SECURITY DEFINER, гранты, view) и прогоняет сценарии от имени
// ролей anon / authenticated / service_role. Ничего не трогает в проде.
//
//   node harness.mjs --repo <путь> [--migrations a.sql,b.sql | (порядок из DEPLOY.md/README.md)]
//                    [--twice x.sql,y.sql] [--scenario s.mjs] [--no-audit] [--json out.json] [--port 54329]
//
// Код выхода: 0 — миграции и сценарий прошли (находки аудита — это отчёт, не ошибка);
//             1 — упала миграция, повтор или сценарий.
import EmbeddedPostgres from 'embedded-postgres';
import pg from 'pg';
import { readFileSync, rmSync, existsSync, mkdtempSync, writeFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const HELP = `Использование:
  node harness.mjs --repo ../my-site
  node harness.mjs --repo ../my-site --migrations supabase.sql,fix.sql --twice fix.sql --scenario checks.mjs
Без --migrations порядок берётся из нумерованного списка *.sql в DEPLOY.md / README.md / docs/*.md.`;

function parseArgs(argv) {
  const a = { repo: '.', migrations: null, twice: [], scenario: null, audit: true, json: null, port: 54329 };
  const list = (s) => String(s || '').split(',').map((x) => x.trim()).filter(Boolean);
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => {
      const val = argv[++i];
      if (val === undefined) throw new Error(`нет значения для ${k}`);
      return val;
    };
    if (k === '--repo') a.repo = v();
    else if (k === '--migrations') a.migrations = list(v());
    else if (k === '--twice') a.twice = list(v());
    else if (k === '--scenario') a.scenario = v();
    else if (k === '--no-audit') a.audit = false;
    else if (k === '--json') a.json = v();
    else if (k === '--port') a.port = Number(v());
    else if (k === '--help' || k === '-h') { console.log(HELP); process.exit(0); }
    else throw new Error(`неизвестный аргумент ${k}\n${HELP}`);
  }
  a.repo = resolve(a.repo);
  return a;
}

// Порядок миграций из документации: строки вида "1. `supabase.sql`" или "2) fix.sql — ...".
function migrationsFromDocs(repo) {
  const docs = ['DEPLOY.md', 'README.md', 'MIGRATIONS.md'].map((f) => join(repo, f));
  const docsDir = join(repo, 'docs');
  if (existsSync(docsDir)) for (const f of readdirSync(docsDir)) if (f.endsWith('.md')) docs.push(join(docsDir, f));
  for (const doc of docs) {
    if (!existsSync(doc)) continue;
    const found = [];
    for (const line of readFileSync(doc, 'utf8').split('\n')) {
      const m = line.match(/^\s*\d+[.)]\s+`?([\w./-]+\.sql)`?/);
      if (m && !found.includes(m[1])) found.push(m[1]);
    }
    if (found.length) return { list: found, source: doc };
  }
  return null;
}

const BOOTSTRAP = [
  // Роли PostgREST/Supabase
  `do $$ begin create role anon nologin noinherit; exception when duplicate_object then null; end $$`,
  `do $$ begin create role authenticated nologin noinherit; exception when duplicate_object then null; end $$`,
  `do $$ begin create role service_role nologin noinherit bypassrls; exception when duplicate_object then null; end $$`,
  `create schema if not exists auth`,
  `create schema if not exists extensions`,
  // auth.* как в Supabase: claims берутся из настроек сессии request.jwt.*
  `create or replace function auth.uid() returns uuid language sql stable as
     $$ select nullif(coalesce(current_setting('request.jwt.claim.sub', true),
                               current_setting('request.jwt.claims', true)::jsonb ->> 'sub'), '')::uuid $$`,
  `create or replace function auth.role() returns text language sql stable as
     $$ select nullif(coalesce(current_setting('request.jwt.claim.role', true),
                               current_setting('request.jwt.claims', true)::jsonb ->> 'role'), '')::text $$`,
  `create or replace function auth.jwt() returns jsonb language sql stable as
     $$ select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$`,
  `create or replace function auth.email() returns text language sql stable as
     $$ select auth.jwt() ->> 'email' $$`,
  `create table if not exists auth.users (
     id uuid primary key default gen_random_uuid(), email text, phone text,
     email_confirmed_at timestamptz, phone_confirmed_at timestamptz,
     raw_user_meta_data jsonb not null default '{}', raw_app_meta_data jsonb not null default '{}',
     created_at timestamptz not null default now())`,
  `create table if not exists auth.mfa_factors (
     id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id) on delete cascade,
     factor_type text not null default 'totp', status text not null default 'verified',
     created_at timestamptz not null default now())`,
  `do $$ begin create publication supabase_realtime; exception when duplicate_object then null; end $$`,
  `grant usage on schema public, auth, extensions to anon, authenticated, service_role`,
  `grant execute on all functions in schema auth to anon, authenticated, service_role`,
  // Как в Supabase: на всё новое в public у anon/authenticated есть права, защищает только RLS.
  `alter default privileges in schema public grant all on tables to anon, authenticated, service_role`,
  `alter default privileges in schema public grant all on sequences to anon, authenticated, service_role`,
  `alter default privileges in schema public grant execute on functions to anon, authenticated, service_role`,
];
const OPTIONAL_EXT = ['pgcrypto', 'uuid-ossp', 'citext', 'pg_trgm'];

function lineOf(sql, position) {
  if (!position) return null;
  return sql.slice(0, Number(position)).split('\n').length;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  let migrations = args.migrations;
  if (!migrations) {
    const fromDocs = migrationsFromDocs(args.repo);
    if (!fromDocs) throw new Error('не нашёл порядок миграций: передайте --migrations a.sql,b.sql');
    migrations = fromDocs.list;
    console.log(`Порядок миграций из ${fromDocs.source}`);
  }
  const missing = [...migrations, ...args.twice].filter((f) => !existsSync(join(args.repo, f)));
  if (missing.length) throw new Error(`нет файлов: ${missing.join(', ')}`);

  const dir = mkdtempSync(join(tmpdir(), 'pg-harness-'));
  const server = new EmbeddedPostgres({
    databaseDir: dir, user: 'postgres', password: 'pw', port: args.port, persistent: false,
    onLog: () => {}, onError: () => {},
  });
  await server.initialise();
  await server.start();
  const db = new pg.Client({ host: '127.0.0.1', port: args.port, user: 'postgres', password: 'pw', database: 'postgres' });
  await db.connect();
  const q = (sql, params) => db.query(sql, params);
  let failed = false;
  const report = { migrations: [], audit: null, scenario: null };

  try {
    for (const s of BOOTSTRAP) await q(s);
    for (const ext of OPTIONAL_EXT) {
      try { await q(`create extension if not exists "${ext}" with schema extensions`); } catch { /* нет в сборке */ }
    }
    await q(`alter database postgres set search_path = "$user", public, extensions`);
    await q(`set search_path = "$user", public, extensions`);

    const apply = async (f, label) => {
      const sql = readFileSync(join(args.repo, f), 'utf8');
      try {
        await q(sql);
        console.log(`✓ ${label} ${f}`);
        report.migrations.push({ file: f, ok: true, label });
      } catch (e) {
        const line = lineOf(sql, e.position);
        console.log(`✗ ОШИБКА ${label} ${f}${line ? ':' + line : ''} → ${e.message}`);
        report.migrations.push({ file: f, ok: false, label, error: e.message, line });
        try { await q('rollback'); } catch { /* вне транзакции */ }
        throw e;
      }
    };
    for (const f of migrations) await apply(f, 'применён');
    for (const f of args.twice) await apply(f, 'повторно применён');

    if (args.audit) report.audit = await audit(q);

    if (args.scenario) {
      const h = helpers(q, args.repo);
      const mod = await import(pathToFileURL(resolve(args.scenario)).href);
      const fn = mod.default ?? mod.run;
      if (typeof fn !== 'function') throw new Error('сценарий должен экспортировать default async function (h)');
      console.log('\n── Сценарий ' + args.scenario);
      await fn(h);
      console.log('\nСЦЕНАРИЙ ПРОЙДЕН');
      report.scenario = { ok: true };
    }
  } catch (e) {
    failed = true;
    if (!report.migrations.some((m) => !m.ok)) {
      console.log(`\n✗ ${e.code === 'ERR_ASSERTION' ? 'Проверка не прошла' : 'Ошибка'}: ${e.message}`);
      report.scenario = { ok: false, error: e.message };
    }
  } finally {
    if (args.json) writeFileSync(args.json, JSON.stringify(report, null, 2));
    await db.end().catch(() => {});
    await server.stop().catch(() => {});
    rmSync(dir, { recursive: true, force: true });
  }
  process.exitCode = failed ? 1 : 0;
}

// Помощники для сценариев: запросы от имени ролей с claims, как их выставляет PostgREST.
function helpers(q, repo) {
  const as = async (role, claims, sql, params) => {
    await q(`select set_config('request.jwt.claims', $1, false), set_config('request.jwt.claim.sub', $2, false),
                    set_config('request.jwt.claim.role', $3, false)`,
      [JSON.stringify(claims), claims.sub ?? '', role]);
    await q(`set role ${role}`);
    try { return await q(sql, params); } finally { await q('reset role'); }
  };
  return {
    q, assert, repo,
    log: (...m) => console.log('✓', ...m),
    asAnon: (sql, params) => as('anon', { role: 'anon' }, sql, params),
    // claims по умолчанию — обычный вход паролем (aal1); для 2FA передайте { aal: 'aal2' }
    asUser: (uid, sql, params, claims = {}) =>
      as('authenticated', { sub: uid, role: 'authenticated', aal: 'aal1', ...claims }, sql, params),
    asService: (sql, params) => as('service_role', { role: 'service_role' }, sql, params),
    createUser: async (fields = {}) => {
      const r = await q(`insert into auth.users (id, email, phone) values (coalesce($1::uuid, gen_random_uuid()), $2, $3) returning id`,
        [fields.id ?? null, fields.email ?? null, fields.phone ?? null]);
      return r.rows[0].id;
    },
    // ожидать отказ: await h.rejects(h.asAnon('select * from t'), /permission denied/)
    rejects: (promise, re) => assert.rejects(promise, re),
  };
}

async function audit(q) {
  const out = {};
  const section = (title, rows, fmt, hint) => {
    console.log(`\n${rows.length ? '⚠' : '✓'} ${title}: ${rows.length || 'нет'}`);
    for (const r of rows) console.log('   - ' + fmt(r));
    if (rows.length && hint) console.log('   → ' + hint);
  };

  out.rlsOff = (await q(`
    select c.relname as table,
           has_table_privilege('anon', c.oid, 'select') as anon_select,
           has_table_privilege('anon', c.oid, 'insert,update,delete') as anon_write
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relkind in ('r','p') and not c.relrowsecurity
    order by 1`)).rows;
  section('Таблицы public без RLS', out.rlsOff,
    (r) => `${r.table}${r.anon_select || r.anon_write ? ' (anon: ' + [r.anon_select && 'select', r.anon_write && 'write'].filter(Boolean).join('+') + ')' : ''}`,
    'enable row level security + политики, либо revoke all ... from anon, authenticated');

  out.openPolicies = (await q(`
    select tablename as table, policyname as policy, cmd, roles::text as roles, qual, with_check
    from pg_policies
    where schemaname = 'public'
      and (roles && array['public','anon','authenticated']::name[])
      and (coalesce(qual, '') = 'true' or coalesce(with_check, '') = 'true')
    order by 1, 2`)).rows;
  section('Политики «true» для public/anon/authenticated', out.openPolicies,
    (r) => `${r.table}.${r.policy} [${r.cmd} ${r.roles}] using=${r.qual ?? '-'} check=${r.with_check ?? '-'}`,
    'для SELECT справочников это норма; для INSERT/UPDATE/DELETE — почти всегда дыра');

  out.definerNoPath = (await q(`
    select p.oid::regprocedure::text as fn
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public' and p.prosecdef
      and not exists (select 1 from unnest(coalesce(p.proconfig, '{}')) c where c like 'search_path=%')
    order by 1`)).rows;
  section('SECURITY DEFINER без set search_path', out.definerNoPath, (r) => r.fn,
    'добавить set search_path = public, pg_temp (иначе подмена объектов через search_path)');

  out.callable = (await q(`
    select p.oid::regprocedure::text as fn, p.prosecdef as definer,
           has_function_privilege('anon', p.oid, 'execute') as anon,
           has_function_privilege('authenticated', p.oid, 'execute') as authed,
           (p.proacl is null or exists (select 1 from aclexplode(p.proacl) a
                                        where a.grantee = 0 and a.privilege_type = 'EXECUTE')) as via_public,
           (p.prosrc ~* '(auth\\.uid|auth\\.jwt|auth\\.role|is_staff|is_admin|current_user|request\\.jwt)') as checks_identity
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public' and p.prokind = 'f' and p.prorettype <> 'trigger'::regtype
      and (has_function_privilege('anon', p.oid, 'execute') or has_function_privilege('authenticated', p.oid, 'execute'))
    order by p.prosecdef desc, 1`)).rows;
  const tag = (r) => [r.anon ? 'anon' : null, r.authed ? 'authenticated' : null].filter(Boolean).join('+')
    + (r.via_public ? ', через PUBLIC' : '') + (r.definer ? ', DEFINER' : '')
    + (r.definer && !r.checks_identity ? ', без проверки личности' : '');
  section('Функции, доступные через /rest/v1/rpc (проверить каждую)', out.callable, (r) => `${r.fn} — ${tag(r)}`,
    out.callable.some((r) => r.via_public)
      ? 'EXECUTE по умолчанию выдан PUBLIC: revoke ... from public, anon, authenticated, затем grant нужным ролям'
      : 'у каждой: кто может вызвать, что проверяет внутри (личность, владение строкой, лимиты), что возвращает');

  out.views = (await q(`
    select c.relname as view,
           coalesce((select option_value from pg_options_to_table(c.reloptions) where option_name = 'security_invoker'), 'false') as invoker,
           has_table_privilege('anon', c.oid, 'select') as anon_select,
           has_table_privilege('authenticated', c.oid, 'select') as authed_select
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relkind in ('v','m')
    order by 1`)).rows.filter((r) => r.invoker !== 'true' && (r.anon_select || r.authed_select));
  section('View без security_invoker, читаемые anon/authenticated (обходят RLS)', out.views,
    (r) => `${r.view} (${[r.anon_select && 'anon', r.authed_select && 'authenticated'].filter(Boolean).join('+')})`,
    'alter view ... set (security_invoker = true) или revoke select ... from anon, authenticated');

  out.anonWrite = (await q(`
    select distinct c.relname as table, p.cmd
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    join pg_policies p on p.schemaname = 'public' and p.tablename = c.relname
    where n.nspname = 'public' and c.relrowsecurity and p.cmd in ('INSERT','UPDATE','DELETE','ALL')
      and (p.roles && array['public','anon']::name[])
      and has_table_privilege('anon', c.oid, 'insert,update,delete')
    order by 1, 2`)).rows;
  section('Таблицы, куда anon может писать напрямую', out.anonWrite, (r) => `${r.table} [${r.cmd}]`,
    'запись с сайта лучше вести через RPC с валидацией и лимитами, а прямые права отозвать');

  out.realtime = (await q(`select tablename as table from pg_publication_tables where pubname = 'supabase_realtime' order by 1`)).rows;
  console.log(`\nℹ Таблицы в supabase_realtime: ${out.realtime.map((r) => r.table).join(', ') || 'нет'}`
    + (out.realtime.length ? ' — подписчики видят строки по тем же SELECT-политикам' : ''));
  return out;
}

main().catch((e) => { console.error('✗', e.message); process.exit(1); });
