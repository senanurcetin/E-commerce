import { validateMeasurementId, validateLabEvent } from "./core.mjs";

const CONSENT_KEY = "nexus_commerce_lab_analytics_consent_v1";

/**
 * Consent-first tracking. NO Google resource, cookie or request is created
 * until the human explicitly allows optional GA4 measurement.
 */
export function createTracker({ measurementId = "", host, doc, storage }) {
  const valid = validateMeasurementId(measurementId);
  let consent = "unset";
  let injected = false;
  try {
    const saved = storage?.getItem(CONSENT_KEY);
    if (saved === "allow" || saved === "deny") consent = saved;
  } catch {
    // Browser storage may be unavailable. Default is no tracking.
  }

  function loadGoogleOnce() {
    if (!valid || consent !== "allow") return false;
    host["ga-disable-" + measurementId] = false;
    if (injected) return true;
    injected = true;
    host.dataLayer = host.dataLayer || [];
    host.gtag = host.gtag || function gtag() {
      host.dataLayer.push(arguments);
    };
    // Explicit consent update. No automatic GA4 pageview is emitted.
    host.gtag("js", new Date());
    host.gtag("config", measurementId, { send_page_view: false });
    const script = doc.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" +
      encodeURIComponent(measurementId);
    doc.head.appendChild(script);
    return true;
  }

  function track(name, params = {}) {
    const checked = validateLabEvent(name, params);
    if (!valid || consent !== "allow") return false;
    loadGoogleOnce();
    host.gtag("event", name, checked);
    return true;
  }

  function choose(value) {
    if (value !== "allow" && value !== "deny") throw new RangeError("Consent must be allow or deny");
    consent = value;
    try {
      storage?.setItem(CONSENT_KEY, value);
    } catch {
      // Consent only persists when storage is available.
    }
    if (value === "allow" && valid) {
      loadGoogleOnce();
      track("lab_page_view");
    } else if (valid && injected) {
      host["ga-disable-" + measurementId] = true;
      host.gtag?.("consent", "update", { analytics_storage: "denied" });
    }
    return snapshot();
  }

  function snapshot() {
    return Object.freeze({
      configured: valid,
      consent,
      active: valid && consent === "allow",
    });
  }

  // Previously recorded user choice can be honored without presenting a
  // duplicate banner; never silently opt in a fresh visitor.
  if (consent === "allow" && valid) {
    loadGoogleOnce();
    track("lab_page_view");
  }

  return { track, choose, snapshot };
}
