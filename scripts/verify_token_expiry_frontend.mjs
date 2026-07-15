import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const FRONTEND_URL = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const CHROME_EXECUTABLE_PATH = process.env.VERIFY_CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });

  await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    localStorage.setItem("access_token", "expired-or-invalid-token");
    localStorage.setItem("username", "expired_user");
    localStorage.setItem("role", "admin");
    localStorage.setItem("position", "operations");
  });

  await page.goto(`${FRONTEND_URL}/dashboard`, { waitUntil: "networkidle" });
  await page.getByText("登录失效", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  const result = {
    modalVisible: await isTextVisible(page, "登录失效"),
    hintVisible: await isTextVisible(page, "登录失效，需要重新登录"),
    publicHomeVisible: await isTextVisible(page, "登录") || await isTextVisible(page, "大模型聊天"),
    dashboardHidden: !(await isTextVisible(page, "岗位数据概览")),
    tokenCleared: await page.evaluate(() => !localStorage.getItem("access_token")),
    returnedHome: new URL(page.url()).pathname === "/",
    currentUrl: page.url(),
  };

  console.log(JSON.stringify(result, null, 2));

  if (!result.modalVisible || !result.hintVisible || !result.publicHomeVisible || !result.dashboardHidden || !result.tokenCleared || !result.returnedHome) {
    throw new Error("token expiry frontend verification failed");
  }
} finally {
  await browser.close();
}


async function isTextVisible(page, text) {
  try {
    return await page.getByText(text, { exact: false }).first().isVisible({
      timeout: 2500,
    });
  } catch {
    return false;
  }
}
