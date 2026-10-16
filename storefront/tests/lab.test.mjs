import test from "node:test";
import assert from "node:assert/strict";
import {
  PRODUCTS, getProduct, normalizeCart, changeCart, cartSummary,
  validateLabEvent, validateMeasurementId, LAB_EVENT_NAMES,
} from "../core.mjs";
import { createTracker } from "../tracking.mjs";

test("catalog contains stable distinct illustrative items", () => {
  assert.equal(PRODUCTS.length, 8);
  assert.equal(new Set(PRODUCTS.map((p) => p.id)).size, PRODUCTS.length);
  assert.equal(getProduct("n-101").name, "Orbit Headphones");
  assert.equal(getProduct("__proto__"), null);
  assert.ok(PRODUCTS.every((p) => p.price > 0 && Number.isSafeInteger(p.price)));
});

test("cart ignores unknown or tampered quantities", () => {
  assert.deepEqual(normalizeCart({ "n-101": 2, invalid: 999, "n-202": -8, "n-302": 5.5 }), { "n-101": 2 });
  assert.deepEqual(normalizeCart(["n-101"]), {});
  assert.deepEqual(normalizeCart(null), {});
});

test("cart changes never exceed item limit or go negative", () => {
  const start = changeCart({}, "n-101", 1);
  assert.equal(start["n-101"], 1);
  const total = cartSummary(start);
  assert.equal(total.illustrativeTotal, 129);
  assert.equal(total.quantity, 1);
  assert.deepEqual(changeCart(start, "n-101", -1), {});
  assert.equal(changeCart({ "n-101": 20 }, "n-101", 1)["n-101"], 20);
  assert.throws(() => changeCart({}, "invalid", 1), /Unknown/);
  assert.throws(() => changeCart({}, "n-101", 100), /Quantity/);
});

test("measurement ID validation only accepts GA4 web IDs", () => {
  assert.equal(validateMeasurementId(""), false);
  assert.equal(validateMeasurementId("G-ABC123456"), true);
  assert.equal(validateMeasurementId("UA-12345-1"), false);
  assert.equal(validateMeasurementId("G-ABC<>123"), false);
  assert.equal(validateMeasurementId("https://bad.example"), false);
});

test("only nonmonetary sandbox events with allowlisted fields", () => {
  assert.equal(LAB_EVENT_NAMES.includes("purchase"), false);
  assert.equal(LAB_EVENT_NAMES.includes("refund"), false);
  assert.equal(LAB_EVENT_NAMES.includes("begin_checkout"), false);
  assert.deepEqual(validateLabEvent("lab_checkout_completed", { quantity: 2 }), {
    lab_environment: "sandbox", lab_catalog: "illustrative", quantity: 2,
  });
  assert.throws(() => validateLabEvent("purchase", { value: 100 }), /Unsupported/);
  assert.throws(() => validateLabEvent("lab_add_to_cart", { transaction_id: "abc" }), /Unexpected/);
  assert.throws(() => validateLabEvent("lab_view_item", { item_id: "bad" }), /Unknown/);
  assert.throws(() => validateLabEvent("lab_checkout_completed", { quantity: 200 }), /Invalid/);
});

function trackerHarness(measurementId, stored = null) {
  const backing = new Map();
  if (stored) backing.set("nexus_commerce_lab_analytics_consent_v1", stored);
  const storage = {
    getItem: (key) => backing.get(key) || null,
    setItem: (key, value) => backing.set(key, value),
  };
  const scripts = [];
  const document = {
    createElement: (tag) => ({ tagName: tag }),
    head: { appendChild: (element) => scripts.push(element) },
  };
  const host = {};
  const tracker = createTracker({ measurementId, host, doc: document, storage });
  return { tracker, host, scripts, backing };
}

test("visitor without consent does not load Google tag or send events", () => {
  const h = trackerHarness("G-ABC123456");
  assert.equal(h.tracker.snapshot().active, false);
  assert.equal(h.tracker.track("lab_view_item", { item_id: "n-101" }), false);
  assert.equal(h.scripts.length, 0);
  assert.equal(h.host.gtag, undefined);
});

test("denial cannot load analytics but consent can load once and emit lab event", () => {
  const h = trackerHarness("G-ABC123456");
  h.tracker.choose("deny");
  assert.equal(h.scripts.length, 0);
  assert.equal(h.tracker.track("lab_add_to_cart", { item_id: "n-101" }), false);
  h.tracker.choose("allow");
  assert.equal(h.scripts.length, 1);
  assert.equal(h.scripts[0].src, "https://www.googletagmanager.com/gtag/js?id=G-ABC123456");
  assert.equal(h.tracker.snapshot().active, true);
  assert.equal(h.tracker.track("lab_add_to_cart", { item_id: "n-101", quantity: 1 }), true);
  const eventNames = h.host.dataLayer.filter((args) => args[0] === "event").map((args) => args[1]);
  assert.deepEqual(eventNames, ["lab_page_view", "lab_add_to_cart"]);
  assert.ok(h.host.dataLayer.every((args) => !(args[1] === "purchase")));
});

test("revoking consent disables future Google measurement calls", () => {
  const h = trackerHarness("G-ABC123456", "allow");
  assert.equal(h.scripts.length, 1);
  h.tracker.choose("deny");
  assert.equal(h.host["ga-disable-G-ABC123456"], true);
  assert.equal(h.tracker.track("lab_checkout_completed", { quantity: 1 }), false);
  assert.equal(h.scripts.length, 1);
});

test("no valid owned property means no tracking, even after opt-in", () => {
  const h = trackerHarness("");
  h.tracker.choose("allow");
  assert.equal(h.tracker.snapshot().active, false);
  assert.equal(h.scripts.length, 0);
  assert.equal(h.tracker.track("lab_page_view"), false);
});
