const sb = supabase.createClient(APP_CONFIG.SUPABASE_URL, APP_CONFIG.SUPABASE_ANON_KEY);
let MENU = [];
let cart = {};
let discount = 0;

function toggleTheme() {
  const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = t;
  localStorage.setItem('theme', t);
}

async function loadMenu() {
  const { data } = await sb.from('menu').select('*').eq('available', true);
  MENU = data || [];
  document.getElementById('menu').innerHTML = MENU.map(m => `
    <div class="pizza">
      <h3>${m.name}</h3>
      <p>${m.price} ₸</p>
      <button onclick="addToCart('${m.id}')">В корзину</button>
    </div>`).join('');
}

function addToCart(id) {
  cart[id] = (cart[id] || 0) + 1;
  renderCart();
}

function total() {
  const sum = Object.entries(cart).reduce((s, [id, q]) => s + MENU.find(m => m.id === id).price * q, 0);
  return Math.round(sum * (100 - discount) / 100);
}

function renderCart() {
  document.getElementById('cartItems').innerHTML = Object.entries(cart).map(([id, q]) => {
    const m = MENU.find(x => x.id === id);
    return `<li>${m.name} × ${q} <button onclick="removeItem('${id}')">✕</button></li>`;
  }).join('');
  document.getElementById('total').textContent = total();
}

function removeItem(id) { delete cart[id]; renderCart(); }

async function applyPromo() {
  const code = document.getElementById('promo').value;
  const { data, error } = await sb.rpc('redeem_promo', { p_code: code });
  if (error) { document.getElementById('msg').textContent = 'Код не подошёл'; return; }
  discount = data;
  renderCart();
}

async function placeOrder(e) {
  e.preventDefault();
  const order = {
    name: document.getElementById('name').value,
    phone: document.getElementById('phone').value,
    address: document.getElementById('address').value,
    items: Object.entries(cart).map(([id, qty]) => ({ id, qty })),
    total: total()
  };
  const { error } = await sb.from('orders').insert(order);
  document.getElementById('msg').innerHTML = error
    ? 'Ошибка: ' + error.message
    : `Спасибо, ${order.name}! Мы позвоним на ${order.phone}.`;
  if (!error) { cart = {}; renderCart(); }
}

loadMenu();
