// Антиспам-шлюз (Supabase Edge Function): проверяет токен Cloudflare Turnstile и только потом
// вызывает RPC из белого списка ACTIONS с сервисным ключом. После lock-миграции
// (revoke execute ... from public, anon, authenticated) эти RPC с anon-ключом напрямую не вызвать.
// Подставьте свои действия в ACTIONS: имя действия = action виджета Turnstile на сайте.
//
// Секреты (Supabase → Edge Functions → Secrets):
//   TURNSTILE_SECRET_KEY — секретный ключ виджета Turnstile (обязательно)
//   ALLOWED_ORIGINS      — сайты, с которых разрешены запросы, через запятую,
//                          напр. "https://my-site.vercel.app" (обязательно)
// SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY Supabase подставляет сам.

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const TURNSTILE_SECRET = Deno.env.get("TURNSTILE_SECRET_KEY") ?? "";
const ALLOWED_ORIGINS = (Deno.env.get("ALLOWED_ORIGINS") ?? "")
  .split(",").map((s) => s.trim().replace(/\/+$/, "")).filter(Boolean);
const ALLOWED_HOSTS = ALLOWED_ORIGINS.map((o) => {
  try { return new URL(o).hostname; } catch { return ""; }
}).filter(Boolean);

const MAX_BODY = 16 * 1024;

type Body = Record<string, unknown>;
type Action = { rpc: string; args: (b: Body) => Record<string, unknown> | null };

// Белый список действий: только эти RPC и только с проверенными аргументами.
const ACTIONS: Record<string, Action> = {
  order: {
    rpc: "place_order",
    args: (b) => {
      const p = b.payload;
      return p && typeof p === "object" && !Array.isArray(p) ? { payload: p } : null;
    },
  },
  wheel: {
    rpc: "spin_wheel",
    args: (b) => (typeof b.phone === "string" && b.phone.length <= 32 ? { p_phone: b.phone } : null),
  },
};

function cors(origin: string): HeadersInit {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGINS.includes(origin) ? origin : "null",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function reply(body: unknown, status: number, origin: string): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors(origin), "Content-Type": "application/json; charset=utf-8" },
  });
}

async function verifyTurnstile(token: string, ip: string | null, action: string): Promise<boolean> {
  const form = new URLSearchParams({ secret: TURNSTILE_SECRET, response: token });
  if (ip) form.set("remoteip", ip);
  try {
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(8000),
    });
    const v = await r.json();
    if (v?.success !== true) return false;
    if (v.action !== action) return false;
    if (ALLOWED_HOSTS.length && !ALLOWED_HOSTS.includes(v.hostname)) return false;
    return true;
  } catch {
    return false;
  }
}

Deno.serve(async (req) => {
  const origin = (req.headers.get("origin") ?? "").replace(/\/+$/, "");

  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
  if (req.method !== "POST") return reply({ message: "method not allowed" }, 405, origin);
  if (!TURNSTILE_SECRET || !ALLOWED_ORIGINS.length || !SUPABASE_URL || !SERVICE_KEY) {
    return reply({ message: "gate not configured" }, 500, origin);
  }
  if (!ALLOWED_ORIGINS.includes(origin)) return reply({ message: "forbidden origin" }, 403, origin);

  const raw = await req.text();
  if (raw.length > MAX_BODY) return reply({ message: "payload too large" }, 413, origin);
  let body: Body;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("bad");
    body = parsed as Body;
  } catch {
    return reply({ message: "bad request" }, 400, origin);
  }

  const name = typeof body.action === "string" ? body.action : "";
  const action = Object.hasOwn(ACTIONS, name) ? ACTIONS[name] : null;
  const token = typeof body.token === "string" ? body.token : "";
  if (!action || !token || token.length > 2048) return reply({ message: "bad request" }, 400, origin);

  const args = action.args(body);
  if (!args) return reply({ message: "bad request" }, 400, origin);

  const ip = req.headers.get("cf-connecting-ip") ??
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? null;
  if (!(await verifyTurnstile(token, ip, name))) {
    return reply({ message: "captcha failed" }, 403, origin);
  }

  const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${action.rpc}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SERVICE_KEY,
      Authorization: `Bearer ${SERVICE_KEY}`,
    },
    body: JSON.stringify(args),
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    // Наружу — только текст ошибки бизнес-логики (лимиты, минимальная сумма и т.п.).
    const message = typeof data?.message === "string" ? data.message.slice(0, 200) : "request failed";
    return reply({ message }, r.status >= 500 ? 502 : 400, origin);
  }
  return reply(data, 200, origin);
});
