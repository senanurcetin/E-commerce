import { validateMeasurementId, validateLabEvent } from "./core.mjs";

const CONSENT_KEY_PREFIX = "nexus_commerce_lab_analytics_consent_v2_";

/**
 * Consent-first tracking. NO Google resource, cookie or request is created
 * until the human explicitly allows optional GA4 measurement.
 */
export function createTracker({ measurementId = "", host, doc, storage }) {
  const valid = validateMeasurementId(measurementId);
  // Never carry a previous property\'s consent to a different GA4 stream.
  const consentKey = valid ? CONSENT_KEY_PREFIX + measurementId : null;
  let consent = "unset";
  let injected = false;
  try {
    const saved = consentKey ? storage?.getItem(consentKey) : null;
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
    // Analytics is disabled until explicit opt-in; even then, never send an\n    // automatic GA4 page_view or purchase event.\n    host.gtag("consent", "default", { analytics_storage: "denied", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied" });\n    host.gtag("consent", "update", { analytics_storage: "granted" });\n    host.gtag("js", new Date());
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
      if (consentKey) storage?.setItem(consentKey, value);
    } catch {
      // Consent only persists when storage is available.
    }
    if (value === "allow" && valid) {
      loadGoogleOnce();
      // Re-approval after a past denial must re-enable Consent Mode too.
      host.gtag?.("consent", "update", { analytics_storage: "granted" });
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
