import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3222";
const TARGETS = process.argv.slice(2);

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1512, height: 950 }, reducedMotion: "reduce" });
const page = await context.newPage();

const seen = new Set();
page.on("console", (m) => {
  if (m.type() !== "error") return;
  const text = m.text();
  if (seen.has(text)) return;
  seen.add(text);
  console.log("\n--- console error ---\n" + text);
});
page.on("pageerror", (e) => {
  const text = `${e.message}\n${e.stack ?? ""}`;
  if (seen.has(text)) return;
  seen.add(text);
  console.log("\n--- page error ---\n" + text);
});

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /^Sign in$/ }).click();
await page.waitForURL(/\/(app|onboarding)/, { timeout: 30000 });

for (const path of TARGETS) {
  console.log(`\n======== ${path} ========`);
  await page.goto(BASE + path, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
}

await browser.close();
