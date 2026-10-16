/** Pure, predictable lab-only storefront data and cart functions. */
export const PRODUCTS = Object.freeze([
  { id: "n-101", name: "Orbit Headphones", category: "Audio", price: 129, label: "SOUND / 01", shape: "orbit", tone: "cyan", blurb: "Spatial sound, considered design and long-session comfort." },
  { id: "n-102", name: "Monarch Speaker", category: "Audio", price: 89, label: "SOUND / 02", shape: "speaker", tone: "violet", blurb: "A compact desktop speaker with a quietly bold silhouette." },
  { id: "n-201", name: "Arc Task Light", category: "Workspace", price: 149, label: "DESK / 01", shape: "lamp", tone: "lime", blurb: "Warm illumination for the spaces where good ideas happen." },
  { id: "n-202", name: "Vector Keyboard", category: "Workspace", price: 109, label: "DESK / 02", shape: "keyboard", tone: "rose", blurb: "Precise keys with an understated studio aesthetic." },
  { id: "n-301", name: "Metro Carryall", category: "Everyday", price: 98, label: "LIFE / 01", shape: "bag", tone: "violet", blurb: "Everyday storage with an adaptable, minimal form." },
  { id: "n-302", name: "Aero Flask", category: "Everyday", price: 34, label: "LIFE / 02", shape: "bottle", tone: "cyan", blurb: "A durable vessel for work, movement and the in-between." },
  { id: "n-401", name: "Halo Wireless Pad", category: "Technology", price: 65, label: "TECH / 01", shape: "pad", tone: "lime", blurb: "Power within reach, without adding visual noise." },
  { id: "n-402", name: "Prism Hub", category: "Technology", price: 79, label: "TECH / 02", shape: "hub", tone: "rose", blurb: "A neat expansion point for an intentional setup." },
]);

export const LAB_EVENT_NAMES = Object.freeze([
  "lab_page_view", "lab_view_item", "lab_add_to_cart",
  "lab_remove_from_cart", "lab_checkout_completed",
]);

const ITEM_LIMIT = 20;
const catalogById = new Map(PRODUCTS.map((p) => [p.id, p]));

export function getProduct(id) {
  return catalogById.get(id) ?? null;
}

export function validateMeasurementId(value) {
  return typeof value === "string" && /^G-[A-Z0-9]{7,15}$/.test(value);
}

export function normalizeCart(value) {
  const output = {};
  if (value === null || typeof value !== "object" || Array.isArray(value)) return output;
  for (const [id, count] of Object.entries(value)) {
    if (!catalogById.has(id)) continue;
    if (!Number.isSafeInteger(count) || count < 1 || count > ITEM_LIMIT) continue;
    output[id] = count;
  }
  return output;
}

export function changeCart(cart, id, delta) {
  if (!catalogById.has(id)) throw new RangeError("Unknown catalog item");
  if (!Number.isSafeInteger(delta) || ![-1, 1].includes(delta)) {
    throw new RangeError("Quantity change must be +1 or -1");
  }
  const next = normalizeCart(cart);
  const count = Math.min(ITEM_LIMIT, Math.max(0, (next[id] ?? 0) + delta));
  if (count) next[id] = count;
  else delete next[id];
  return next;
}

export function cartSummary(cart) {
  const entries = Object.entries(normalizeCart(cart)).map(([id, count]) => ({
    product: catalogById.get(id), quantity: count,
  }));
  const quantity = entries.reduce((sum, x) => sum + x.quantity, 0);
  const total = entries.reduce((sum, x) => sum + x.quantity * x.product.price, 0);
  return { entries, quantity, illustrativeTotal: total };
}

export function validateLabEvent(eventName, params = {}) {
  if (!LAB_EVENT_NAMES.includes(eventName)) throw new RangeError("Unsupported lab event");
  const keys = Object.keys(params);
  const allowed = ["item_id", "quantity"];
  if (keys.some((key) => !allowed.includes(key))) {
    throw new RangeError("Unexpected lab event parameter");
  }
  if ("item_id" in params && !catalogById.has(params.item_id)) {
    throw new RangeError("Unknown item ID");
  }
  if ("quantity" in params && (!Number.isSafeInteger(params.quantity) || params.quantity < 1 || params.quantity > ITEM_LIMIT)) {
    throw new RangeError("Invalid quantity");
  }
  return Object.freeze({
    lab_environment: "sandbox",
    lab_catalog: "illustrative",
    ...params,
  });
}
