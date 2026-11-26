-- Pizza Napoli: базовая схема
create table if not exists public.menu (
  id text primary key,
  name text not null,
  price int not null check (price > 0),
  available boolean not null default true
);
alter table public.menu enable row level security;
create policy menu_read on public.menu for select using (true);

create table if not exists public.orders (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  name text not null,
  phone text not null,
  address text not null,
  items jsonb not null,
  total int not null,
  status text not null default 'new',
  paid boolean not null default false
);
alter table public.orders enable row level security;
create policy orders_insert on public.orders for insert with check (true);
create policy orders_read on public.orders for select using (true);

create table if not exists public.staff (
  id uuid primary key references auth.users(id),
  name text not null,
  role text not null default 'operator'
);

create or replace view public.orders_today as
  select id, name, phone, address, total, status from public.orders
  where created_at > now() - interval '1 day';

create or replace function public.mark_paid(p_order bigint)
returns void language plpgsql security definer as $$
begin
  update public.orders set paid = true, status = 'paid' where id = p_order;
end $$;

create or replace function public.set_status(p_order bigint, p_status text)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from public.staff where id = auth.uid()) then
    raise exception 'not staff';
  end if;
  update public.orders set status = p_status where id = p_order;
end $$;

insert into public.menu (id, name, price) values
  ('margherita', 'Маргарита', 2900), ('pepperoni', 'Пепперони', 3400), ('quattro', 'Четыре сыра', 3800)
on conflict (id) do nothing;
