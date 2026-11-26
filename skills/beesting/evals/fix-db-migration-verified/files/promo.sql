-- Pizza Napoli: промокоды
create table if not exists public.promo_codes (
  code text primary key,
  discount int not null check (discount between 1 and 50),
  used boolean not null default false
);
alter table public.promo_codes enable row level security;

create or replace function public.redeem_promo(p_code text)
returns int language plpgsql security definer as $$
declare d int;
begin
  select discount into d from public.promo_codes where code = upper(p_code);
  if d is null then raise exception 'bad code'; end if;
  update public.promo_codes set used = true where code = upper(p_code);
  return d;
end $$;

insert into public.promo_codes (code, discount) values ('WELCOME10', 10), ('VIP50', 50)
on conflict (code) do nothing;
