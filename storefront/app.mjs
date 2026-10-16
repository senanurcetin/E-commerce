import { PRODUCTS, normalizeCart, changeCart, cartSummary } from "./core.mjs";
import { createTracker } from "./tracking.mjs";

const el = (id) => document.getElementById(id);
const KEY = "nexus_commerce_lab_cart_v1";
const tracker = createTracker({
  measurementId: window.NEXUS_LAB_CONFIG?.ga4MeasurementId ?? "",
  host: window, doc: document, storage: window.localStorage,
});
const state = { cart: {}, filter: "All", overlay: null, previousFocus: null };

try { state.cart = normalizeCart(JSON.parse(localStorage.getItem(KEY) || "{}")); }
catch { state.cart = {}; }
function save() { try { localStorage.setItem(KEY, JSON.stringify(state.cart)); } catch { /* no storage */ } }
function money(n) { return "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 }); }
function addText(parent, tag, label, className) {
  const node = document.createElement(tag);
  node.textContent = label;
  if (className) node.className = className;
  parent.append(node);
  return node;
}
function toast(message) {
  const node = addText(document.body, "div", message, "lab-toast");
  node.setAttribute("role", "status");
  setTimeout(() => node.remove(), 3500);
}
function renderFilters() {
  const parent = el("category-filters");
  parent.replaceChildren();
  for (const category of ["All", ...new Set(PRODUCTS.map((p) => p.category))]) {
    const button = addText(parent, "button", category, category === state.filter ? "selected" : "");
    button.type = "button";
    button.setAttribute("aria-pressed", String(category === state.filter));
    button.addEventListener("click", () => {
      state.filter = category;
      renderFilters();
      renderProducts();
    });
  }
}
function createProduct(product) {
  const article = document.createElement("article");
  article.className = "product-card";
  const art = document.createElement("div");
  art.className = "product-art tone-" + product.tone + " shape-" + product.shape;
  art.setAttribute("role", "img");
  art.setAttribute("aria-label", "Abstract illustration of " + product.name);
  addText(art, "span", product.label, "item-index");
  addText(art, "span", "", "visual");
  art.addEventListener("click", () => tracker.track("lab_view_item", { item_id: product.id }));
  article.append(art);
  const info = document.createElement("div");
  info.className = "product-info";
  addText(info, "span", product.category.toUpperCase() + " · NEXUS EDITION", "product-meta");
  addText(info, "h3", product.name);
  addText(info, "p", product.blurb);
  const bottom = document.createElement("div");
  bottom.className = "product-bottom";
  const amount = document.createElement("div");
  addText(amount, "span", money(product.price), "price");
  addText(amount, "span", "Illustrative price", "sample-note");
  bottom.append(amount);
  const button = addText(bottom, "button", "+ Add to test cart", "add-cart");
  button.type = "button";
  button.addEventListener("click", () => {
    const old = state.cart[product.id] ?? 0;
    state.cart = changeCart(state.cart, product.id, 1);
    if ((state.cart[product.id] ?? 0) === old) {
      toast("Test cart item limit reached");
      return;
    }
    save();
    renderCart();
    tracker.track("lab_add_to_cart", { item_id: product.id, quantity: 1 });
    toast(product.name + " added to test cart");
  });
  info.append(bottom);
  article.append(info);
  return article;
}
function renderProducts() {
  const grid = el("product-grid");
  grid.replaceChildren();
  for (const p of PRODUCTS) {
    if (state.filter === "All" || p.category === state.filter) grid.append(createProduct(p));
  }
}
function changeQuantity(id, delta) {
  const before = state.cart[id] ?? 0;
  state.cart = changeCart(state.cart, id, delta);
  if ((state.cart[id] ?? 0) === before) return;
  save();
  renderCart();
  tracker.track(delta > 0 ? "lab_add_to_cart" : "lab_remove_from_cart", { item_id: id, quantity: 1 });
}
function renderCart() {
  const summary = cartSummary(state.cart);
  el("cart-count").textContent = String(summary.quantity);
  el("cart-total").textContent = money(summary.illustrativeTotal);
  el("checkout-button").disabled = summary.quantity === 0;
  const items = el("cart-items");
  items.replaceChildren();
  if (!summary.quantity) {
    addText(items, "p", "Your test cart is empty. Browse the collection to add an object.", "cart-empty");
    return;
  }
  for (const item of summary.entries) {
    const node = document.createElement("div");
    node.className = "cart-item";
    addText(node, "div", "N", "mini-art");
    const main = document.createElement("div");
    main.className = "cart-item-main";
    addText(main, "strong", item.product.name);
    addText(main, "small", money(item.product.price) + " · illustrative");
    const controls = document.createElement("div");
    controls.className = "qty-row";
    const less = addText(controls, "button", "−", "decrease");
    less.setAttribute("aria-label", "Remove one " + item.product.name);
    less.addEventListener("click", () => changeQuantity(item.product.id, -1));
    addText(controls, "span", String(item.quantity));
    const more = addText(controls, "button", "+", "increase");
    more.setAttribute("aria-label", "Add one " + item.product.name);
    more.addEventListener("click", () => changeQuantity(item.product.id, 1));
    main.append(controls);
    node.append(main);
    items.append(node);
  }
}
function openOverlay(which) {
  state.previousFocus = document.activeElement;
  state.overlay = which;
  el("shade").hidden = false;
  el("cart-panel").hidden = which !== "cart";
  el("checkout-modal").hidden = which !== "checkout";
  document.body.classList.add("overlay-open");
  (which === "cart" ? el("cart-panel") : el("checkout-modal")).focus();
}
function closeOverlay() {
  if (!state.overlay) return;
  state.overlay = null;
  el("shade").hidden = true;
  el("cart-panel").hidden = true;
  el("checkout-modal").hidden = true;
  document.body.classList.remove("overlay-open");
  state.previousFocus?.focus?.();
}
function checkout() {
  const summary = cartSummary(state.cart);
  if (!summary.quantity) return;
  // No purchase, monetary amount, customer data or order ID sent.
  tracker.track("lab_checkout_completed", { quantity: summary.quantity });
  state.cart = {};
  save();
  renderCart();
  closeOverlay();
  openOverlay("checkout");
}
function updateConsent() {
  const snapshot = tracker.snapshot();
  const pill = el("tracking-status");
  pill.textContent = !snapshot.configured ? "GA4 not connected"
    : snapshot.active ? "Analytics opt-in" : "Analytics off";
  pill.classList.toggle("enabled", snapshot.active);
  el("consent-bar").hidden = !snapshot.configured || snapshot.consent !== "unset";
}
el("open-cart").addEventListener("click", () => openOverlay("cart"));
el("close-cart").addEventListener("click", closeOverlay);
el("shade").addEventListener("click", closeOverlay);
el("checkout-button").addEventListener("click", checkout);
el("close-checkout").addEventListener("click", closeOverlay);
el("allow-analytics").addEventListener("click", () => { tracker.choose("allow"); updateConsent(); });
el("deny-analytics").addEventListener("click", () => { tracker.choose("deny"); updateConsent(); });
el("manage-consent").addEventListener("click", () => {
  if (!tracker.snapshot().configured) {
    toast("No owned GA4 property is configured. No analytics is sent.");
  } else {
    el("consent-bar").hidden = false;
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.overlay) closeOverlay();
  if (event.key !== "Tab" || !state.overlay) return;
  const panel = state.overlay === "cart" ? el("cart-panel") : el("checkout-modal");
  const choices = [...panel.querySelectorAll("button:not([disabled]),a[href],input:not([disabled])")];
  if (!choices.length) return;
  const first = choices[0], last = choices[choices.length - 1];
  if (event.shiftKey && [first, panel].includes(document.activeElement)) {
    last.focus(); event.preventDefault();
  } else if (!event.shiftKey && document.activeElement === last) {
    first.focus(); event.preventDefault();
  }
});
renderFilters();
renderProducts();
renderCart();
updateConsent();
