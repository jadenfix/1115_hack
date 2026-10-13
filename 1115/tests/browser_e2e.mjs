import {existsSync} from "node:fs";
import {mkdtemp, mkdir} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, resolve} from "node:path";
import {spawn} from "node:child_process";
import process from "node:process";
import {createConnection} from "node:net";
import {chromium} from "playwright-core";

const root = resolve(import.meta.dirname, "..");
const temporal = process.env.TEMPORAL_CLI || "temporal";
const virtualenvPython = join(root, ".venv", "bin", "python");
const python = process.env.PYTHON || (existsSync(virtualenvPython) ? virtualenvPython : "python3");
const chromiumPath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || chromium.executablePath();
const address = "127.0.0.1:7331";
const baseUrl = "http://127.0.0.1:8011";
const dataDir = await mkdtemp(join(tmpdir(), "1115-browser-e2e-"));
const processes = [];
const logs = [];
let browser = null;

function launch(command, args, extraEnv = {}) {
  const child = spawn(command, args, {
    cwd: root,
    env: {...process.env, ...extraEnv},
    stdio: ["ignore", "pipe", "pipe"],
  });
  child.stdout.on("data", (chunk) => logs.push(chunk.toString()));
  child.stderr.on("data", (chunk) => logs.push(chunk.toString()));
  child.on("error", (error) => logs.push(`PROCESS_ERROR ${command}: ${error.message}\n`));
  processes.push(child);
  return child;
}

async function waitForPort(port, attempts = 120) {
  for (let count = 0; count < attempts; count += 1) {
    const connected = await new Promise((resolveConnection) => {
      const socket = createConnection({host: "127.0.0.1", port});
      socket.once("connect", () => { socket.destroy(); resolveConnection(true); });
      socket.once("error", () => resolveConnection(false));
      socket.setTimeout(200, () => { socket.destroy(); resolveConnection(false); });
    });
    if (connected) return;
    await new Promise((resolveWait) => setTimeout(resolveWait, 150));
  }
  throw new Error(`Port did not become ready: ${port}`);
}

async function waitForLog(fragment, attempts = 120) {
  for (let count = 0; count < attempts; count += 1) {
    if (logs.join("").includes(fragment)) return;
    await new Promise((resolveWait) => setTimeout(resolveWait, 150));
  }
  throw new Error(`Process readiness log not observed: ${fragment}`);
}

async function waitForHttp(url, attempts = 100) {
  for (let count = 0; count < attempts; count += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch (_) {}
    await new Promise((resolveWait) => setTimeout(resolveWait, 150));
  }
  throw new Error(`Service did not become ready: ${url}`);
}

async function capture(page, name) {
  if (!process.env.CAPTURE_DIR) return;
  await mkdir(process.env.CAPTURE_DIR, {recursive: true});
  await page.screenshot({path: join(process.env.CAPTURE_DIR, `${name}.png`), fullPage: true});
}

function stopAll() {
  for (const child of processes.reverse()) {
    if (!child.killed) child.kill("SIGTERM");
  }
}

process.on("exit", stopAll);
process.on("SIGINT", () => { stopAll(); process.exit(130); });

try {
  launch(temporal, ["server", "start-dev", "--headless", "--port", "7331", "--db-filename", join(dataDir, "temporal.db")]);
  await waitForPort(7331);
  const serviceEnv = {
    DATA_DIR: join(dataDir, "data"),
    TEMPORAL_ADDRESS: address,
    LINKUP_API_KEY: "fixture-must-not-call",
    BROWSER_USE_API_KEY: "fixture-must-not-call",
    ANTHROPIC_API_KEY: "fixture-must-not-call",
    FREEPIC_API_KEY: "fixture-must-not-call",
    LINKUP_BASE_URL: "http://127.0.0.1:9",
    BROWSER_USE_BASE_URL: "http://127.0.0.1:9",
    SMARTBUCKETS_BASE_URL: "http://127.0.0.1:9",
    FREEPIC_BASE_URL: "http://127.0.0.1:9",
  };
  launch(python, ["-m", "app.worker"], serviceEnv);
  launch(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8011"], serviceEnv);
  await waitForLog("Worker started on queue");
  await waitForHttp(`${baseUrl}/health`);

  browser = await chromium.launch({executablePath: chromiumPath, headless: true, args: ["--no-sandbox"]});
  const page = await browser.newPage({viewport: {width: 1440, height: 1050}, deviceScaleFactor: 1});
  const browserErrors = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.goto(baseUrl, {waitUntil: "networkidle"});
  await capture(page, "01-ready");
  await page.click("#demo-btn");
  await page.waitForFunction(() => document.querySelector("#status-pill")?.textContent === "Completed", null, {timeout: 60000});
  await page.waitForSelector("#snapshot-card .fixture-stamp");
  await page.waitForFunction(() => document.querySelectorAll("#evidence-body tr").length === 3);
  await capture(page, "02-complete");
  await page.click('[data-tab="evidence"]');
  await capture(page, "03-evidence");
  await page.click('[data-tab="outreach"]');
  await capture(page, "04-outreach");
  await page.click('[data-tab="visual"]');
  await capture(page, "05-visual");

  await page.route("**/api/snapshot/malicious", async (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      company: {name: "<img src=x onerror=document.body.dataset.pwned='yes'>", domain: "<svg onload=document.body.dataset.pwned='yes'>", persona: "attacker"},
      mode: "live", policy_version: "xss-check", linkup_results: [],
      pages: [{url: "javascript:alert(1)", page_type: "<img src=x onerror=alert(1)>", usefulness_score: 0.4, signals: ["<svg onload=alert(1)>"]}],
      brief_md: "<img src=x onerror=document.body.dataset.pwned='yes'>",
      outreach_message: "<script>document.body.dataset.pwned='yes'</script>",
    }),
  }));
  await page.evaluate(() => loadSnapshot("malicious"));
  await page.waitForFunction(() => document.querySelector("#snapshot-title")?.textContent?.startsWith("<img"));
  const safety = await page.evaluate(() => ({
    pwned: document.body.dataset.pwned || "no",
    injectedImages: document.querySelectorAll("#snapshot-card img").length,
    unsafeLinks: document.querySelectorAll('#evidence-body a[href^="javascript:"]').length,
    literalText: document.querySelector("#snapshot-card")?.textContent?.includes("<svg"),
  }));
  if (safety.pwned !== "no" || safety.injectedImages !== 0 || safety.unsafeLinks !== 0 || !safety.literalText) {
    throw new Error(`DOM safety check failed: ${JSON.stringify(safety)}`);
  }
  if (browserErrors.length) throw new Error(`Browser errors: ${browserErrors.join(" | ")}`);
  await browser.close();
  browser = null;
  console.log("BROWSER_E2E_OK fixture=3-pages temporal=real processes=separate dom_xss=blocked providers=0");
} catch (error) {
  console.error(error);
  console.error(logs.join(""));
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  stopAll();
}
