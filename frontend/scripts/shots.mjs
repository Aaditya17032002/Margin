import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const BASE = process.env.BASE ?? "http://localhost:3111";
const OUT = "shots";

const PAGES = [
  ["landing", "/", { full: true }],
  ["pricing", "/pricing", { full: true }],
  ["login", "/login"],
  ["signup", "/signup"],
  ["onboarding", "/onboarding"],
  ["not-found", "/nope"],
  ["style", "/style", { full: true }],
  ["dashboard", "/app", { auth: true, full: true }],
  ["board", "/app/analyses", { auth: true }],
  ["new", "/app/analyses/new", { auth: true }],
  ["workspace", "/app/analyses/an_tea_dlp", { auth: true, full: true }],
  ["matrix-tab", "/app/analyses/an_tea_dlp?tab=matrix", { auth: true }],
  ["questions-tab", "/app/analyses/an_tea_dlp?tab=questions", { auth: true }],
  ["deadlines", "/app/deadlines", { auth: true }],
  ["matrix", "/app/matrix", { auth: true }],
  ["knowledge", "/app/knowledge", { auth: true }],
  ["templates", "/app/templates", { auth: true }],
  ["reports", "/app/reports", { auth: true }],
  ["integrations", "/app/integrations", { auth: true }],
  ["team", "/app/team", { auth: true }],
  ["settings", "/app/settings", { auth: true }],
  ["help", "/app/help", { auth: true }],
];

const errors = [];

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1512, height: 950 },
  deviceScaleFactor: 2,
  reducedMotion: "reduce",
});
context.on("weberror", (e) => errors.push(`[weberror] ${e.error().message}`));

await mkdir(OUT, { recursive: true });

const page = await context.newPage();
page.on("console", (m) => {
  if (m.type() === "error") errors.push(`[console] ${m.text()}`);
});
page.on("pageerror", (e) => errors.push(`[pageerror] ${e.message}`));

// Sign in once; the session persists in localStorage for the whole context.
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /^Sign in$/ }).click();
await page.waitForURL(/\/(app|onboarding)/, { timeout: 15000 });
if (page.url().includes("/onboarding")) {
  await page.evaluate(() => {
    const raw = localStorage.getItem("margin.session");
    if (!raw) return;
    const parsed = JSON.parse(raw);
    parsed.state.onboarded = true;
    localStorage.setItem("margin.session", JSON.stringify(parsed));
  });
}

for (const [name, path, opts = {}] of PAGES) {
  const before = errors.length;
  await page.goto(BASE + path, { waitUntil: "networkidle" });
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: Boolean(opts.full) });
  const added = errors.slice(before);
  console.log(`${name.padEnd(16)} ${path.padEnd(42)} ${added.length ? "ERRORS " + added.length : "ok"}`);
  for (const e of added) console.log("    " + e.slice(0, 300));
}

await browser.close();
console.log(`\n${errors.length} console/page errors total`);
