import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const BASE = process.env.BASE ?? "http://localhost:3111";
const OUT = "shots";
const ID = "an_tea_dlp";

const errors = [];
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1512, height: 950 },
  deviceScaleFactor: 2,
  reducedMotion: "reduce",
});
await mkdir(OUT, { recursive: true });
const page = await context.newPage();
page.on("console", (m) => m.type() === "error" && errors.push(m.text().slice(0, 200)));
page.on("pageerror", (e) => errors.push("[pageerror] " + e.message.slice(0, 200)));

const step = async (name, fn) => {
  const before = errors.length;
  await fn();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/x-${name}.png` });
  const added = errors.slice(before);
  console.log(`${name.padEnd(24)} ${added.length ? "ERRORS" : "ok"}`);
  added.forEach((e) => console.log("    " + e));
};

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /^Sign in$/ }).click();
await page.waitForURL(/\/(app|onboarding)/, { timeout: 20000 });

await step("workspace-rail-hint", async () => {
  await page.goto(`${BASE}/app/analyses/${ID}`, { waitUntil: "networkidle" });
});

await step("workspace-rail-open", async () => {
  await page.locator("button, a").filter({ hasText: /p\.\s*\d+/ }).first().hover();
});

await step("command-palette", async () => {
  await page.keyboard.press("Control+k");
});

await step("board-kanban", async () => {
  await page.keyboard.press("Escape");
  await page.goto(`${BASE}/app/analyses`, { waitUntil: "networkidle" });
});

await step("board-table", async () => {
  const table = page.getByRole("radio", { name: /table/i }).or(page.getByRole("tab", { name: /table/i }));
  if (await table.count()) await table.first().click();
});

await step("matrix-grid", async () => {
  await page.goto(`${BASE}/app/analyses/${ID}?tab=matrix`, { waitUntil: "networkidle" });
});

await step("qa-builder", async () => {
  await page.goto(`${BASE}/app/analyses/${ID}?tab=questions`, { waitUntil: "networkidle" });
});

await step("reading-room", async () => {
  await page.goto(`${BASE}/app/analyses/new`, { waitUntil: "networkidle" });
});

await step("dusk", async () => {
  await page.goto(`${BASE}/app/settings?tab=appearance`, { waitUntil: "networkidle" });
  const dusk = page.getByRole("radio", { name: /dusk/i }).or(page.getByRole("button", { name: /dusk/i }));
  if (await dusk.count()) await dusk.first().click();
});

await step("dusk-dashboard", async () => {
  await page.goto(`${BASE}/app`, { waitUntil: "networkidle" });
});

await browser.close();
console.log(`\n${errors.length} errors`);
