import { cp, mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { validateMeasurementId } from "../core.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = resolve(root, "dist");
const supplied = (process.env.NEXUS_GA4_MEASUREMENT_ID || "").trim();
if (supplied && !validateMeasurementId(supplied)) {
  throw new Error("Invalid NEXUS_GA4_MEASUREMENT_ID. Expected public GA4 G-XXXXXXXX Measurement ID.");
}
await mkdir(dist, { recursive: true });
for (const file of ["index.html", "styles.css", "app.mjs", "core.mjs", "tracking.mjs"]) {
  await cp(resolve(root, file), resolve(dist, file));
}
await writeFile(
  resolve(dist, "config.js"),
  "/* Public measurement configuration (never store tokens or secrets here). */\n" +
  "window.NEXUS_LAB_CONFIG = Object.freeze({ ga4MeasurementId: " + JSON.stringify(supplied) + " });\n",
  "utf8",
);
console.log("Built NEXUS Commerce Lab: " + dist + "; GA4 " + (supplied ? "configured; consent required" : "not configured"));
