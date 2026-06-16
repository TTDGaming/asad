// ============ Asad Store SPA ============
const App = document.getElementById("app");
const state = {
  token: localStorage.getItem("token") || "",
  user: null,
  settings: {},
  categories: [],
  cartCount: 0,
};

// Bắt mã giới thiệu từ link ?ref=CODE
const refMatch = new URLSearchParams(location.search).get("ref");
if (refMatch) localStorage.setItem("ref", refMatch);

// ---------- helpers ----------
const money = (n) => (n || 0).toLocaleString("vi-VN") + "đ";
const fmtDate = (s) => new Date(s).toLocaleString("vi-VN");
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

function toast(msg, kind = "") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show " + kind;
  setTimeout(() => (t.className = "toast " + kind), 2600);
}

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = "Bearer " + state.token;
  const res = await fetch("/api" + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && state.token) {
      logout(true);
    }
    throw new Error(data.detail || "Có lỗi xảy ra");
  }
  return data;
}

function setToken(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("token", token);
}

function logout(silent) {
  state.token = "";
  state.user = null;
  localStorage.removeItem("token");
  if (!silent) {
    toast("Đã đăng xuất");
    location.hash = "#/";
  }
  renderNav();
  router();
}

// ---------- nav ----------
function renderNav() {
  const nav = document.getElementById("topnav");
  const u = state.user;
  let html = `<a href="#/">🏠 Cửa hàng</a>`;
  if (u) {
    html += `<a href="#/cart">🛒 Giỏ<span class="badge-count" id="cartBadge">${state.cartCount}</span></a>`;
    html += `<a href="#/orders">📦 Đơn</a>`;
    html += `<a href="#/affiliate">🤝 Affiliate</a>`;
    html += `<a href="#/wallet" class="pill-balance">💰 ${money(u.balance)}</a>`;
    if (u.role === "admin") html += `<a href="#/admin">⚙️ Admin</a>`;
    html += `<a href="#/profile">👤 ${esc(u.username)}</a>`;
    html += `<button onclick="logout()">Thoát</button>`;
  } else {
    html += `<a href="#/login">Đăng nhập</a>`;
  }
  nav.innerHTML = html;
}

function updateCartBadge() {
  const b = document.getElementById("cartBadge");
  if (b) b.textContent = state.cartCount;
}

async function refreshCartCount() {
  if (!state.token) {
    state.cartCount = 0;
    return;
  }
  try {
    const cart = await api("GET", "/cart");
    state.cartCount = cart.reduce((s, i) => s + i.quantity, 0);
    updateCartBadge();
  } catch {}
}

// ---------- router ----------
function parseHash() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query] = raw.split("?");
  return { parts: path.split("/").filter(Boolean), query: new URLSearchParams(query || "") };
}

async function router() {
  const { parts, query } = parseHash();
  const root = parts[0] || "";
  try {
    if (root === "" ) return viewHome(query);
    if (root === "p") return viewProduct(parts[1]);
    if (root === "login") return viewAuth();
    if (root === "cart") return guard(viewCart);
    if (root === "orders") return guard(viewOrders);
    if (root === "wallet") return guard(viewWallet);
    if (root === "affiliate") return guard(viewAffiliate);
    if (root === "profile") return guard(viewProfile);
    if (root === "admin") return guardAdmin(() => viewAdmin(query));
    viewHome(query);
  } catch (e) {
    App.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

function guard(fn) {
  if (!state.user) {
    location.hash = "#/login";
    return;
  }
  return fn();
}
function guardAdmin(fn) {
  if (!state.user || state.user.role !== "admin") {
    toast("Yêu cầu quyền quản trị", "err");
    location.hash = "#/";
    return;
  }
  return fn();
}

// ============ VIEWS ============
async function viewHome(query) {
  const active = query.get("cat") || "";
  const search = document.getElementById("searchInput").value.trim();
  let path = "/products?";
  if (active) path += "category=" + encodeURIComponent(active) + "&";
  if (search) path += "search=" + encodeURIComponent(search);
  const [products] = await Promise.all([api("GET", path)]);

  let chips = `<a href="#/" class="chip ${active ? "" : "active"}">Tất cả</a>`;
  for (const c of state.categories)
    chips += `<a href="#/?cat=${c.slug}" class="chip ${active === c.slug ? "active" : ""}">${c.icon || ""} ${esc(c.name)}</a>`;

  let cards = products.map(productCard).join("");
  if (!products.length) cards = `<div class="empty">Không có sản phẩm phù hợp.</div>`;

  App.innerHTML = `
    <div class="hero">
      <h1>${esc(state.settings.site_name || "Asad Store")}</h1>
      <p>${esc(state.settings.site_tagline || "Cửa hàng số tự động — giao hàng tức thì 24/7")}</p>
    </div>
    <div class="chips">${chips}</div>
    <div class="grid products">${cards}</div>`;
}

function productCard(p) {
  const thumb = p.image_url
    ? `<img src="${esc(p.image_url)}" alt="">`
    : (state.categories.find((c) => c.id === p.category_id)?.icon || "🛍️");
  const stock = p.stock_count > 0
    ? `<span class="stock-ok">Còn ${p.stock_count}</span>`
    : `<span class="stock-out">Hết hàng</span>`;
  return `
    <a class="product-card" href="#/p/${p.slug}">
      <div class="product-thumb">${thumb}</div>
      <div class="product-body">
        <div class="product-name">${esc(p.name)}</div>
        <div class="muted">${stock} · Đã bán ${p.sold_count}</div>
        <div class="product-meta">
          <span class="price">${money(p.price)}</span>
          <span class="tag">Chi tiết →</span>
        </div>
      </div>
    </a>`;
}

async function viewProduct(slug) {
  const p = await api("GET", "/products/" + slug);
  const cat = state.categories.find((c) => c.id === p.category_id);
  const thumb = p.image_url
    ? `<img src="${esc(p.image_url)}" alt="">`
    : (cat?.icon || "🛍️");
  const inStock = p.stock_count > 0;
  App.innerHTML = `
    <a href="#/" class="muted">← Quay lại cửa hàng</a>
    <div class="card" style="margin-top:12px">
      <div class="row">
        <div style="max-width:320px"><div class="product-thumb" style="height:200px;border-radius:12px">${thumb}</div></div>
        <div style="flex:2">
          <h1 class="section-title">${esc(p.name)}</h1>
          <p class="muted">${cat ? esc(cat.name) + " · " : ""}Đã bán ${p.sold_count}</p>
          <div class="price" style="font-size:26px">${money(p.price)}</div>
          <p style="margin:14px 0">${esc(p.description || "")}</p>
          <p>${inStock ? `<span class="stock-ok">✔ Còn ${p.stock_count} sản phẩm · giao tự động</span>` : `<span class="stock-out">Tạm hết hàng</span>`}</p>
          <div class="row" style="margin-top:14px">
            <button class="btn" ${inStock ? "" : "disabled"} onclick="addToCart(${p.id})">🛒 Thêm vào giỏ</button>
            <button class="btn green" ${inStock ? "" : "disabled"} onclick="buyNow(${p.id})">⚡ Mua ngay</button>
          </div>
        </div>
      </div>
    </div>`;
}

async function addToCart(productId) {
  if (!state.user) { location.hash = "#/login"; return; }
  try {
    await api("POST", "/cart", { product_id: productId, quantity: 1 });
    await refreshCartCount();
    toast("Đã thêm vào giỏ", "ok");
  } catch (e) { toast(e.message, "err"); }
}

async function buyNow(productId) {
  if (!state.user) { location.hash = "#/login"; return; }
  try {
    await api("POST", "/cart", { product_id: productId, quantity: 1 });
    await refreshCartCount();
    location.hash = "#/cart";
  } catch (e) { toast(e.message, "err"); }
}

async function viewCart() {
  const cart = await api("GET", "/cart");
  state.cartCount = cart.reduce((s, i) => s + i.quantity, 0);
  updateCartBadge();
  if (!cart.length) {
    App.innerHTML = `<h1 class="section-title">Giỏ hàng</h1><div class="empty">Giỏ hàng trống. <a href="#/" style="color:var(--brand)">Mua sắm ngay →</a></div>`;
    return;
  }
  const total = cart.reduce((s, i) => s + i.product.price * i.quantity, 0);
  const rows = cart.map((i) => `
    <tr>
      <td>${esc(i.product.name)}<div class="muted">${money(i.product.price)}</div></td>
      <td>
        <div class="row" style="max-width:140px">
          <button class="btn ghost sm" onclick="setQty(${i.id}, ${i.quantity - 1})">−</button>
          <span style="align-self:center">${i.quantity}</span>
          <button class="btn ghost sm" onclick="setQty(${i.id}, ${i.quantity + 1})">+</button>
        </div>
      </td>
      <td>${money(i.product.price * i.quantity)}</td>
      <td><button class="btn red sm" onclick="removeCart(${i.id})">Xóa</button></td>
    </tr>`).join("");
  App.innerHTML = `
    <h1 class="section-title">Giỏ hàng</h1>
    <div class="card table-wrap">
      <table><thead><tr><th>Sản phẩm</th><th>SL</th><th>Tạm tính</th><th></th></tr></thead><tbody>${rows}</tbody></table>
    </div>
    <div class="card flex-between">
      <div>Số dư ví: <b>${money(state.user.balance)}</b></div>
      <div style="text-align:right">
        <div style="font-size:20px">Tổng: <b class="price">${money(total)}</b></div>
        <button class="btn green" style="margin-top:10px" onclick="checkout()">⚡ Thanh toán tự động</button>
      </div>
    </div>`;
}

async function setQty(id, qty) {
  try {
    if (qty < 1) return removeCart(id);
    await api("PATCH", "/cart/" + id, { quantity: qty });
    viewCart();
  } catch (e) { toast(e.message, "err"); }
}
async function removeCart(id) {
  try { await api("DELETE", "/cart/" + id); await refreshCartCount(); viewCart(); }
  catch (e) { toast(e.message, "err"); }
}

async function checkout() {
  try {
    const order = await api("POST", "/orders/checkout");
    state.user.balance -= order.total;
    renderNav();
    await refreshCartCount();
    toast("Đặt hàng thành công! Giao hàng tự động ✔", "ok");
    showOrder(order);
  } catch (e) { toast(e.message, "err"); }
}

function showOrder(order) {
  const items = order.items.map((it) => `
    <div class="card2" style="margin-bottom:10px">
      <div class="flex-between"><b>${esc(it.product_name)}</b><span>${money(it.price)} × ${it.quantity}</span></div>
      <div class="muted" style="margin:6px 0">Sản phẩm đã giao tự động:</div>
      <div class="code-box">${esc(it.delivered_content || "(không có nội dung)")}</div>
    </div>`).join("");
  App.innerHTML = `
    <h1 class="section-title">✅ Đơn ${esc(order.code)}</h1>
    <div class="card">
      <div class="flex-between"><span>Trạng thái</span><span class="status ${order.status}">${order.status}</span></div>
      <div class="flex-between" style="margin-top:6px"><span>Tổng tiền</span><b class="price">${money(order.total)}</b></div>
      <div class="flex-between" style="margin-top:6px"><span>Thời gian</span><span>${fmtDate(order.created_at)}</span></div>
    </div>
    <div class="card"><h3>Nội dung sản phẩm số</h3>${items}</div>
    <a class="btn ghost" href="#/orders">Xem tất cả đơn hàng</a>`;
}

async function viewOrders() {
  const orders = await api("GET", "/orders");
  if (!orders.length) {
    App.innerHTML = `<h1 class="section-title">Đơn hàng của tôi</h1><div class="empty">Chưa có đơn nào.</div>`;
    return;
  }
  const rows = orders.map((o) => `
    <tr style="cursor:pointer" onclick='showOrder(${JSON.stringify(o).replace(/'/g, "&#39;")})'>
      <td><b>${esc(o.code)}</b></td>
      <td>${o.items.length} SP</td>
      <td>${money(o.total)}</td>
      <td><span class="status ${o.status}">${o.status}</span></td>
      <td class="muted">${fmtDate(o.created_at)}</td>
    </tr>`).join("");
  App.innerHTML = `
    <h1 class="section-title">Đơn hàng của tôi</h1>
    <div class="card table-wrap"><table>
      <thead><tr><th>Mã đơn</th><th>SP</th><th>Tổng</th><th>Trạng thái</th><th>Thời gian</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
}

async function viewWallet() {
  const [txs, withdrawals] = await Promise.all([
    api("GET", "/wallet/transactions"),
    api("GET", "/wallet/withdrawals"),
  ]);
  const txRows = txs.map((t) => `
    <tr>
      <td><span class="tag">${t.type}</span></td>
      <td style="color:${t.amount >= 0 ? "var(--green)" : "var(--red)"}">${t.amount >= 0 ? "+" : ""}${money(t.amount)}</td>
      <td>${money(t.balance_after)}</td>
      <td class="muted">${esc(t.note || "")}</td>
      <td class="muted">${fmtDate(t.created_at)}</td>
    </tr>`).join("") || `<tr><td colspan="5" class="muted">Chưa có giao dịch</td></tr>`;
  const wRows = withdrawals.map((w) => `
    <tr><td>${money(w.amount)}</td><td>${esc(w.method)}</td><td>${esc(w.account_info)}</td>
    <td><span class="status ${w.status}">${w.status}</span></td><td class="muted">${fmtDate(w.created_at)}</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">Chưa có yêu cầu rút</td></tr>`;

  App.innerHTML = `
    <h1 class="section-title">Ví của tôi</h1>
    <div class="card flex-between">
      <div><div class="muted">Số dư khả dụng</div><div class="price" style="font-size:30px">${money(state.user.balance)}</div></div>
    </div>
    <div class="row">
      <div class="card">
        <h3>Nạp tiền tự động</h3>
        <div class="form-row"><input id="depAmount" type="number" placeholder="Số tiền (đ)" value="100000"></div>
        <div class="row">
          ${[50000, 100000, 200000, 500000].map((v) => `<button class="btn ghost sm" onclick="document.getElementById('depAmount').value=${v}">${money(v)}</button>`).join("")}
        </div>
        <button class="btn green full" style="margin-top:10px" onclick="deposit()">Nạp ngay</button>
      </div>
      <div class="card">
        <h3>Rút tiền</h3>
        <div class="form-row"><input id="wAmount" type="number" placeholder="Số tiền rút"></div>
        <div class="form-row"><select id="wMethod"><option>Bank</option><option>Momo</option><option>ZaloPay</option><option>USDT</option></select></div>
        <div class="form-row"><input id="wInfo" placeholder="Số TK / SĐT nhận tiền"></div>
        <button class="btn full" onclick="requestWithdraw()">Gửi yêu cầu rút</button>
      </div>
    </div>
    <div class="card table-wrap"><h3>Lịch sử giao dịch</h3>
      <table><thead><tr><th>Loại</th><th>Số tiền</th><th>Số dư</th><th>Ghi chú</th><th>Thời gian</th></tr></thead><tbody>${txRows}</tbody></table>
    </div>
    <div class="card table-wrap"><h3>Yêu cầu rút tiền</h3>
      <table><thead><tr><th>Số tiền</th><th>Phương thức</th><th>Tài khoản</th><th>Trạng thái</th><th>Thời gian</th></tr></thead><tbody>${wRows}</tbody></table>
    </div>`;
}

async function deposit() {
  const amount = parseFloat(document.getElementById("depAmount").value);
  try {
    await api("POST", "/wallet/deposit", { amount });
    state.user.balance += amount;
    renderNav();
    toast("Nạp tiền thành công", "ok");
    viewWallet();
  } catch (e) { toast(e.message, "err"); }
}

async function requestWithdraw() {
  const amount = parseFloat(document.getElementById("wAmount").value);
  const method = document.getElementById("wMethod").value;
  const account_info = document.getElementById("wInfo").value;
  try {
    const w = await api("POST", "/wallet/withdraw", { amount, method, account_info });
    state.user.balance -= w.amount;
    renderNav();
    toast("Đã gửi yêu cầu rút tiền", "ok");
    viewWallet();
  } catch (e) { toast(e.message, "err"); }
}

async function viewAffiliate() {
  const a = await api("GET", "/affiliate");
  const comm = a.commissions.map((c) => `
    <tr><td>#${c.order_id}</td><td>${(c.rate * 100).toFixed(1)}%</td>
    <td style="color:var(--green)">+${money(c.amount)}</td>
    <td><span class="status ${c.status}">${c.status}</span></td><td class="muted">${fmtDate(c.created_at)}</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">Chưa có hoa hồng</td></tr>`;
  const refs = a.referrals.map((r) => `<tr><td>${esc(r.username)}</td><td class="muted">${fmtDate(r.created_at)}</td></tr>`).join("")
    || `<tr><td colspan="2" class="muted">Chưa có ai đăng ký qua link của bạn</td></tr>`;
  App.innerHTML = `
    <h1 class="section-title">🤝 Tiếp thị liên kết (Affiliate)</h1>
    <div class="stats-grid grid">
      <div class="stat"><div class="v">${a.total_referrals}</div><div class="k">Người giới thiệu</div></div>
      <div class="stat"><div class="v" style="color:var(--green)">${money(a.total_earned)}</div><div class="k">Tổng hoa hồng</div></div>
      <div class="stat"><div class="v">${esc(a.referral_code)}</div><div class="k">Mã giới thiệu</div></div>
    </div>
    <div class="card">
      <h3>Link giới thiệu của bạn</h3>
      <div class="row">
        <input id="refLink" value="${esc(a.referral_link)}" readonly>
        <button class="btn" style="max-width:120px" onclick="copyRef()">Sao chép</button>
      </div>
      <p class="muted" style="margin-top:8px">Chia sẻ link này. Mỗi khi người được giới thiệu mua hàng, bạn nhận hoa hồng tự động vào ví.</p>
    </div>
    <div class="card table-wrap"><h3>Hoa hồng</h3>
      <table><thead><tr><th>Đơn</th><th>Tỷ lệ</th><th>Hoa hồng</th><th>Trạng thái</th><th>Thời gian</th></tr></thead><tbody>${comm}</tbody></table>
    </div>
    <div class="card table-wrap"><h3>Người bạn đã giới thiệu</h3>
      <table><thead><tr><th>Tài khoản</th><th>Ngày tham gia</th></tr></thead><tbody>${refs}</tbody></table>
    </div>`;
}

function copyRef() {
  const el = document.getElementById("refLink");
  el.select();
  navigator.clipboard?.writeText(el.value);
  toast("Đã sao chép link", "ok");
}

async function viewProfile() {
  const u = state.user;
  App.innerHTML = `
    <h1 class="section-title">Tài khoản</h1>
    <div class="card">
      <div class="flex-between"><span class="muted">Tên đăng nhập</span><b>${esc(u.username)}</b></div>
      <div class="flex-between" style="margin-top:8px"><span class="muted">Email</span><b>${esc(u.email)}</b></div>
      <div class="flex-between" style="margin-top:8px"><span class="muted">Vai trò</span><span class="tag">${u.role}</span></div>
      <div class="flex-between" style="margin-top:8px"><span class="muted">Số dư</span><b class="price">${money(u.balance)}</b></div>
      <div class="flex-between" style="margin-top:8px"><span class="muted">Mã giới thiệu</span><b>${esc(u.referral_code)}</b></div>
    </div>
    <div class="card">
      <h3>Cập nhật thông tin</h3>
      <div class="form-row"><label>Họ tên</label><input id="pfName" value="${esc(u.full_name || "")}"></div>
      <div class="form-row"><label>Đổi mật khẩu (để trống nếu không đổi)</label><input id="pfPass" type="password" placeholder="Mật khẩu mới"></div>
      <button class="btn" onclick="saveProfile()">Lưu thay đổi</button>
    </div>`;
}

async function saveProfile() {
  const full_name = document.getElementById("pfName").value;
  const password = document.getElementById("pfPass").value;
  try {
    const u = await api("PATCH", "/auth/me", { full_name, password: password || null });
    state.user = u;
    renderNav();
    toast("Đã lưu", "ok");
    viewProfile();
  } catch (e) { toast(e.message, "err"); }
}

// ---------- Auth ----------
function viewAuth() {
  const ref = localStorage.getItem("ref") || "";
  App.innerHTML = `
    <div class="auth-wrap">
      <div class="tabs">
        <div class="tab active" id="tabLogin" onclick="switchAuth('login')">Đăng nhập</div>
        <div class="tab" id="tabReg" onclick="switchAuth('register')">Đăng ký</div>
      </div>
      <div class="card" id="authForm"></div>
    </div>`;
  renderLogin();
}
let authMode = "login";
function switchAuth(mode) {
  authMode = mode;
  document.getElementById("tabLogin").classList.toggle("active", mode === "login");
  document.getElementById("tabReg").classList.toggle("active", mode === "register");
  mode === "login" ? renderLogin() : renderRegister();
}
function renderLogin() {
  document.getElementById("authForm").innerHTML = `
    <div class="form-row"><label>Email hoặc tên đăng nhập</label><input id="lId"></div>
    <div class="form-row"><label>Mật khẩu</label><input id="lPass" type="password"></div>
    <button class="btn full" onclick="doLogin()">Đăng nhập</button>`;
}
function renderRegister() {
  const ref = localStorage.getItem("ref") || "";
  document.getElementById("authForm").innerHTML = `
    <div class="form-row"><label>Email</label><input id="rEmail" type="email"></div>
    <div class="form-row"><label>Tên đăng nhập</label><input id="rUser"></div>
    <div class="form-row"><label>Họ tên</label><input id="rName"></div>
    <div class="form-row"><label>Mật khẩu</label><input id="rPass" type="password"></div>
    <div class="form-row"><label>Mã giới thiệu (nếu có)</label><input id="rRef" value="${esc(ref)}"></div>
    <button class="btn full green" onclick="doRegister()">Tạo tài khoản</button>`;
}
async function doLogin() {
  try {
    const data = await api("POST", "/auth/login", {
      identifier: document.getElementById("lId").value,
      password: document.getElementById("lPass").value,
    });
    setToken(data.token, data.user);
    await afterLogin();
  } catch (e) { toast(e.message, "err"); }
}
async function doRegister() {
  try {
    const data = await api("POST", "/auth/register", {
      email: document.getElementById("rEmail").value,
      username: document.getElementById("rUser").value,
      full_name: document.getElementById("rName").value,
      password: document.getElementById("rPass").value,
      referral_code: document.getElementById("rRef").value || null,
    });
    localStorage.removeItem("ref");
    setToken(data.token, data.user);
    await afterLogin();
  } catch (e) { toast(e.message, "err"); }
}
async function afterLogin() {
  toast("Xin chào " + state.user.username, "ok");
  renderNav();
  await refreshCartCount();
  renderNav();
  location.hash = "#/";
}

// ============ ADMIN ============
async function viewAdmin(query) {
  const tab = query.get("tab") || "dashboard";
  const tabs = [
    ["dashboard", "Tổng quan"], ["products", "Sản phẩm"], ["categories", "Danh mục"],
    ["orders", "Đơn hàng"], ["users", "Người dùng"], ["withdrawals", "Rút tiền"], ["settings", "Cài đặt"],
  ];
  const navHtml = tabs.map(([k, label]) =>
    `<button class="${tab === k ? "active" : ""}" onclick="location.hash='#/admin?tab=${k}'">${label}</button>`).join("");
  App.innerHTML = `<h1 class="section-title">⚙️ Quản trị</h1><div class="admin-nav">${navHtml}</div><div id="adminBody"><div class="empty">Đang tải...</div></div>`;
  const body = document.getElementById("adminBody");
  if (tab === "dashboard") return adminDashboard(body);
  if (tab === "products") return adminProducts(body);
  if (tab === "categories") return adminCategories(body);
  if (tab === "orders") return adminOrders(body);
  if (tab === "users") return adminUsers(body);
  if (tab === "withdrawals") return adminWithdrawals(body);
  if (tab === "settings") return adminSettings(body);
}

async function adminDashboard(body) {
  const s = await api("GET", "/admin/stats");
  const stat = (v, k) => `<div class="stat"><div class="v">${v}</div><div class="k">${k}</div></div>`;
  const low = s.low_stock.map((l) => `<tr><td>${esc(l.name)}</td><td class="stock-out">${l.stock}</td></tr>`).join("")
    || `<tr><td colspan="2" class="muted">Tất cả còn đủ hàng</td></tr>`;
  const top = s.top_products.map((t) => `<tr><td>${esc(t.name)}</td><td>${t.sold}</td><td>${money(t.revenue)}</td></tr>`).join("")
    || `<tr><td colspan="3" class="muted">Chưa có dữ liệu</td></tr>`;
  body.innerHTML = `
    <div class="stats-grid grid">
      ${stat(money(s.revenue), "Doanh thu")}
      ${stat(s.orders, "Đơn hàng")}
      ${stat(s.users, "Người dùng")}
      ${stat(s.products, "Sản phẩm")}
      ${stat(s.pending_withdrawals, "Chờ rút tiền")}
      ${stat(money(s.commissions_paid), "Hoa hồng đã trả")}
    </div>
    <div class="row">
      <div class="card table-wrap"><h3>⚠️ Sắp hết hàng</h3><table><thead><tr><th>Sản phẩm</th><th>Tồn</th></tr></thead><tbody>${low}</tbody></table></div>
      <div class="card table-wrap"><h3>🔥 Bán chạy</h3><table><thead><tr><th>Sản phẩm</th><th>Đã bán</th><th>Doanh thu</th></tr></thead><tbody>${top}</tbody></table></div>
    </div>`;
}

async function adminProducts(body) {
  const [products, cats] = await Promise.all([api("GET", "/admin/products"), api("GET", "/admin/categories")]);
  state.categories = cats;
  const opts = (sel) => `<option value="">— Danh mục —</option>` + cats.map((c) => `<option value="${c.id}" ${sel === c.id ? "selected" : ""}>${esc(c.name)}</option>`).join("");
  const rows = products.map((p) => `
    <tr>
      <td>${esc(p.name)}<div class="muted">${p.slug}</div></td>
      <td>${money(p.price)}</td>
      <td>${(p.commission_rate * 100).toFixed(0)}%</td>
      <td class="${p.stock_count > 0 ? "stock-ok" : "stock-out"}">${p.stock_count}</td>
      <td>${p.sold_count}</td>
      <td>${p.is_active ? "✅" : "⛔"}</td>
      <td>
        <button class="btn ghost sm" onclick='openProduct(${JSON.stringify(p)})'>Sửa</button>
        <button class="btn ghost sm" onclick='openStock(${p.id}, ${JSON.stringify(p.name)})'>Kho</button>
        <button class="btn red sm" onclick="delProduct(${p.id})">Xóa</button>
      </td>
    </tr>`).join("");
  body.innerHTML = `
    <button class="btn" onclick='openProduct(null)'>+ Thêm sản phẩm</button>
    <div id="prodForm"></div>
    <div class="card table-wrap" style="margin-top:14px"><table>
      <thead><tr><th>Tên</th><th>Giá</th><th>HH</th><th>Tồn</th><th>Đã bán</th><th>Bật</th><th></th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  window._catOpts = opts;
}

function openProduct(p) {
  const f = document.getElementById("prodForm");
  const v = p || { name: "", category_id: "", price: 0, commission_rate: 0.1, description: "", image_url: "", is_active: true, auto_delivery: true };
  f.innerHTML = `
    <div class="card" style="margin-top:14px">
      <h3>${p ? "Sửa" : "Thêm"} sản phẩm</h3>
      <div class="row">
        <div class="form-row"><label>Tên</label><input id="fName" value="${esc(v.name)}"></div>
        <div class="form-row"><label>Danh mục</label><select id="fCat">${window._catOpts(v.category_id)}</select></div>
      </div>
      <div class="row">
        <div class="form-row"><label>Giá (đ)</label><input id="fPrice" type="number" value="${v.price}"></div>
        <div class="form-row"><label>Hoa hồng (0-1)</label><input id="fRate" type="number" step="0.01" value="${v.commission_rate}"></div>
      </div>
      <div class="form-row"><label>Ảnh URL</label><input id="fImg" value="${esc(v.image_url || "")}"></div>
      <div class="form-row"><label>Mô tả</label><textarea id="fDesc" rows="3">${esc(v.description || "")}</textarea></div>
      <div class="row">
        <label class="checkbox"><input type="checkbox" id="fActive" ${v.is_active ? "checked" : ""}> Đang bán</label>
        <label class="checkbox"><input type="checkbox" id="fAuto" ${v.auto_delivery ? "checked" : ""}> Giao tự động</label>
      </div>
      <button class="btn green" onclick="saveProduct(${p ? p.id : "null"})">Lưu</button>
      <button class="btn ghost" onclick="document.getElementById('prodForm').innerHTML=''">Hủy</button>
    </div>`;
}

async function saveProduct(id) {
  const payload = {
    name: document.getElementById("fName").value,
    category_id: parseInt(document.getElementById("fCat").value) || null,
    price: parseFloat(document.getElementById("fPrice").value) || 0,
    commission_rate: parseFloat(document.getElementById("fRate").value) || 0,
    image_url: document.getElementById("fImg").value || null,
    description: document.getElementById("fDesc").value || null,
    is_active: document.getElementById("fActive").checked,
    auto_delivery: document.getElementById("fAuto").checked,
  };
  try {
    if (id) await api("PATCH", "/admin/products/" + id, payload);
    else await api("POST", "/admin/products", payload);
    toast("Đã lưu sản phẩm", "ok");
    adminProducts(document.getElementById("adminBody"));
  } catch (e) { toast(e.message, "err"); }
}

async function delProduct(id) {
  if (!confirm("Xóa sản phẩm này?")) return;
  try { await api("DELETE", "/admin/products/" + id); toast("Đã xóa", "ok"); adminProducts(document.getElementById("adminBody")); }
  catch (e) { toast(e.message, "err"); }
}

async function openStock(pid, name) {
  const data = await api("GET", `/admin/products/${pid}/stock`);
  const f = document.getElementById("prodForm");
  const avail = data.available.map((s) => `<tr><td class="code-box" style="border:none;padding:4px">${esc(s.content)}</td><td><button class="btn red sm" onclick="delStock(${s.id}, ${pid}, ${JSON.stringify(name)})">x</button></td></tr>`).join("")
    || `<tr><td class="muted">Kho trống</td></tr>`;
  f.innerHTML = `
    <div class="card" style="margin-top:14px">
      <h3>Kho hàng: ${esc(name)}</h3>
      <p class="muted">Còn ${data.available.length} · Đã bán ${data.sold}</p>
      <div class="form-row"><label>Thêm mã/key (mỗi dòng một sản phẩm)</label><textarea id="stockLines" rows="5" placeholder="KEY-001&#10;KEY-002"></textarea></div>
      <button class="btn green" onclick="addStock(${pid}, ${JSON.stringify(name)})">Nhập kho</button>
      <button class="btn ghost" onclick="document.getElementById('prodForm').innerHTML=''">Đóng</button>
      <div class="table-wrap" style="margin-top:12px"><table><tbody>${avail}</tbody></table></div>
    </div>`;
}
async function addStock(pid, name) {
  try {
    const r = await api("POST", `/admin/products/${pid}/stock`, { lines: document.getElementById("stockLines").value });
    toast(`Đã nhập ${r.added} mã`, "ok");
    openStock(pid, name);
    adminProducts.refresh = true;
  } catch (e) { toast(e.message, "err"); }
}
async function delStock(sid, pid, name) {
  try { await api("DELETE", "/admin/stock/" + sid); openStock(pid, name); }
  catch (e) { toast(e.message, "err"); }
}

async function adminCategories(body) {
  const cats = await api("GET", "/admin/categories");
  const rows = cats.map((c) => `
    <tr><td>${c.icon || ""} ${esc(c.name)}</td><td class="muted">${c.slug}</td><td class="muted">${esc(c.description || "")}</td>
    <td><button class="btn red sm" onclick="delCat(${c.id})">Xóa</button></td></tr>`).join("");
  body.innerHTML = `
    <div class="card">
      <h3>Thêm danh mục</h3>
      <div class="row">
        <input id="cName" placeholder="Tên danh mục">
        <input id="cIcon" placeholder="Emoji (vd 🎮)" style="max-width:120px">
      </div>
      <div class="form-row" style="margin-top:10px"><input id="cDesc" placeholder="Mô tả"></div>
      <button class="btn green" onclick="addCat()">Thêm</button>
    </div>
    <div class="card table-wrap"><table><thead><tr><th>Tên</th><th>Slug</th><th>Mô tả</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
async function addCat() {
  try {
    await api("POST", "/admin/categories", {
      name: document.getElementById("cName").value,
      icon: document.getElementById("cIcon").value || null,
      description: document.getElementById("cDesc").value || null,
    });
    await loadCategories();
    toast("Đã thêm danh mục", "ok");
    adminCategories(document.getElementById("adminBody"));
  } catch (e) { toast(e.message, "err"); }
}
async function delCat(id) {
  if (!confirm("Xóa danh mục này?")) return;
  try { await api("DELETE", "/admin/categories/" + id); await loadCategories(); adminCategories(document.getElementById("adminBody")); }
  catch (e) { toast(e.message, "err"); }
}

async function adminOrders(body) {
  const orders = await api("GET", "/admin/orders");
  const rows = orders.map((o) => `
    <tr><td><b>${esc(o.code)}</b></td><td>User #${o.user_id}</td><td>${o.items.length}</td>
    <td>${money(o.total)}</td><td><span class="status ${o.status}">${o.status}</span></td><td class="muted">${fmtDate(o.created_at)}</td></tr>`).join("")
    || `<tr><td colspan="6" class="muted">Chưa có đơn hàng</td></tr>`;
  body.innerHTML = `<div class="card table-wrap"><table>
    <thead><tr><th>Mã</th><th>Khách</th><th>SP</th><th>Tổng</th><th>Trạng thái</th><th>Thời gian</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

async function adminUsers(body) {
  const users = await api("GET", "/admin/users");
  const rows = users.map((u) => `
    <tr>
      <td>${esc(u.username)}<div class="muted">${esc(u.email)}</div></td>
      <td><span class="tag">${u.role}</span></td>
      <td>${money(u.balance)}</td>
      <td>${u.is_active ? "✅" : "⛔"}</td>
      <td>
        <button class="btn ghost sm" onclick="adjBalance(${u.id})">±Tiền</button>
        <button class="btn ghost sm" onclick="toggleRole(${u.id}, '${u.role}')">${u.role === "admin" ? "Hạ" : "Lên Admin"}</button>
        <button class="btn ${u.is_active ? "red" : "green"} sm" onclick="toggleActive(${u.id}, ${u.is_active})">${u.is_active ? "Khóa" : "Mở"}</button>
      </td>
    </tr>`).join("");
  body.innerHTML = `<div class="card table-wrap"><table>
    <thead><tr><th>Người dùng</th><th>Vai trò</th><th>Số dư</th><th>Hoạt động</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}
async function adjBalance(id) {
  const amount = parseFloat(prompt("Cộng/trừ số dư (số âm để trừ):", "0"));
  if (isNaN(amount)) return;
  try { await api("POST", `/admin/users/${id}/balance`, { amount, note: "Admin điều chỉnh" }); toast("Đã cập nhật số dư", "ok"); adminUsers(document.getElementById("adminBody")); }
  catch (e) { toast(e.message, "err"); }
}
async function toggleRole(id, role) {
  try { await api("PATCH", "/admin/users/" + id, { role: role === "admin" ? "user" : "admin" }); adminUsers(document.getElementById("adminBody")); }
  catch (e) { toast(e.message, "err"); }
}
async function toggleActive(id, active) {
  try { await api("PATCH", "/admin/users/" + id, { is_active: !active }); adminUsers(document.getElementById("adminBody")); }
  catch (e) { toast(e.message, "err"); }
}

async function adminWithdrawals(body) {
  const list = await api("GET", "/admin/withdrawals");
  const rows = list.map((w) => `
    <tr>
      <td>User #${w.user_id}</td><td>${money(w.amount)}</td><td>${esc(w.method)}</td><td>${esc(w.account_info)}</td>
      <td><span class="status ${w.status}">${w.status}</span></td>
      <td>${w.status === "pending" ? `
        <button class="btn green sm" onclick="processW(${w.id}, 'approved')">Duyệt</button>
        <button class="btn red sm" onclick="processW(${w.id}, 'rejected')">Từ chối</button>` : (w.note ? esc(w.note) : "—")}</td>
    </tr>`).join("") || `<tr><td colspan="6" class="muted">Chưa có yêu cầu</td></tr>`;
  body.innerHTML = `<div class="card table-wrap"><table>
    <thead><tr><th>Khách</th><th>Số tiền</th><th>PT</th><th>Tài khoản</th><th>Trạng thái</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}
async function processW(id, status) {
  let note = null;
  if (status === "rejected") note = prompt("Lý do từ chối:", "") || "";
  try { await api("POST", "/admin/withdrawals/" + id, { status, note }); toast("Đã xử lý", "ok"); adminWithdrawals(document.getElementById("adminBody")); }
  catch (e) { toast(e.message, "err"); }
}

async function adminSettings(body) {
  const s = await api("GET", "/admin/settings");
  const fields = [
    ["site_name", "Tên cửa hàng"], ["site_tagline", "Khẩu hiệu"], ["support_contact", "Liên hệ hỗ trợ"],
  ];
  body.innerHTML = `<div class="card">
    <h3>Cài đặt cửa hàng</h3>
    ${fields.map(([k, label]) => `<div class="form-row"><label>${label}</label><input id="set_${k}" value="${esc(s[k] || "")}"></div>`).join("")}
    <button class="btn green" onclick='saveSettings(${JSON.stringify(fields.map((f) => f[0]))})'>Lưu cài đặt</button>
  </div>`;
}
async function saveSettings(keys) {
  try {
    for (const k of keys) await api("PUT", "/admin/settings", { key: k, value: document.getElementById("set_" + k).value });
    await loadSettings();
    applyBranding();
    toast("Đã lưu cài đặt", "ok");
  } catch (e) { toast(e.message, "err"); }
}

// ---------- bootstrap ----------
async function loadCategories() {
  try { state.categories = await api("GET", "/categories"); } catch {}
}
async function loadSettings() {
  try { state.settings = await api("GET", "/settings"); } catch {}
}
function applyBranding() {
  const name = state.settings.site_name || "Asad Store";
  document.getElementById("brandName").textContent = name;
  document.getElementById("footerName").textContent = name;
  document.title = name;
}

let searchTimer;
document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    if (!location.hash || location.hash === "#/" || location.hash.startsWith("#/?")) router();
    else location.hash = "#/";
  }, 350);
});

window.addEventListener("hashchange", router);

async function boot() {
  await Promise.all([loadSettings(), loadCategories()]);
  applyBranding();
  if (state.token) {
    try {
      state.user = await api("GET", "/auth/me");
      await refreshCartCount();
    } catch { state.token = ""; localStorage.removeItem("token"); }
  }
  renderNav();
  router();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}
boot();
