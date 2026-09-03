import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3111";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1512, height: 950 } });
page.on("console", (m) => console.log(`[${m.type()}] ${m.text().slice(0, 400)}`));
page.on("pageerror", (e) => console.log(`[pageerror] ${e.message.slice(0, 400)}`));

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
console.log("\nBUTTONS:");
for (const b of await page.getByRole("button").all()) {
  console.log("  -", JSON.stringify((await b.textContent())?.trim()));
}
await page.screenshot({ path: "shots/_probe.png" });
await browser.close();
