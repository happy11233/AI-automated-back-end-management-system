const { app, BrowserWindow, clipboard, ipcMain, shell } = require("electron");
const fs = require("fs/promises");
const path = require("path");
const { createConversationStore } = require("./conversation_store.cjs");

const DEV_SERVER_URL = "http://127.0.0.1:5174";
const streamControllers = new Map();

function createMainWindow() {
  const window = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 980,
    minHeight: 680,
    title: "企业内部工作台",
    frame: false,
    backgroundColor: "#f7f9fc",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (app.isPackaged) {
    window.loadFile(path.join(__dirname, "../dist/index.html"));
  } else {
    window.loadURL(DEV_SERVER_URL);
  }

  window.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  createMainWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

ipcMain.handle("window:minimize", (event) => {
  BrowserWindow.fromWebContents(event.sender)?.minimize();
});

ipcMain.handle("window:maximize", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (!window) return false;
  if (window.isMaximized()) {
    window.unmaximize();
    return false;
  }
  window.maximize();
  return true;
});

ipcMain.handle("window:close", (event) => {
  BrowserWindow.fromWebContents(event.sender)?.close();
});

async function ensureDirectory(directory) {
  await fs.mkdir(directory, { recursive: true });
}

ipcMain.handle("api:request", async (_event, payload) => {
  const response = await fetch(payload.url, {
    method: payload.method,
    headers: payload.headers,
    body: payload.body,
  });
  const body = await response.text();

  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    body,
  };
});

ipcMain.on("api:stream:abort", (_event, payload) => {
  const requestId = String(payload?.requestId || "");
  if (!requestId) return;
  streamControllers.get(requestId)?.abort();
});

ipcMain.handle("api:stream", async (event, payload) => {
  const requestId = String(payload?.requestId || "");
  const channel = String(payload?.channel || "");
  const controller = new AbortController();
  if (requestId) {
    streamControllers.set(requestId, controller);
  }

  const sendStreamItem = (item) => {
    if (!channel || event.sender.isDestroyed()) return;
    event.sender.send(channel, item);
  };

  try {
    const response = await fetch(payload.url, {
      method: payload.method,
      headers: payload.headers,
      body: payload.body,
      signal: controller.signal,
    });

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        statusText: response.statusText,
        body: await response.text(),
      };
    }

    if (!response.body) {
      return {
        ok: false,
        status: response.status,
        statusText: "No response body",
        body: "当前环境不支持流式读取",
      };
    }

    const decoder = new TextDecoder("utf-8");
    for await (const chunk of response.body) {
      if (controller.signal.aborted) break;
      sendStreamItem({
        chunk: decoder.decode(chunk, { stream: true }),
      });
    }
    const tail = decoder.decode();
    if (tail && !controller.signal.aborted) {
      sendStreamItem({ chunk: tail });
    }

    return {
      ok: !controller.signal.aborted,
      status: controller.signal.aborted ? 499 : response.status,
      statusText: controller.signal.aborted ? "Aborted" : response.statusText,
      body: controller.signal.aborted ? "已停止当前任务" : "",
    };
  } catch (error) {
    if (controller.signal.aborted || error?.name === "AbortError") {
      return {
        ok: false,
        status: 499,
        statusText: "Aborted",
        body: "已停止当前任务",
      };
    }
    return {
      ok: false,
      status: 500,
      statusText: "Stream Error",
      body: error?.message || "流式请求失败",
    };
  } finally {
    sendStreamItem({ done: true });
    if (requestId) {
      streamControllers.delete(requestId);
    }
  }
});

function parseDownloadFilename(disposition, fallback) {
  if (!disposition) return fallback;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch?.[1] || fallback;
}

function safeFilename(filename) {
  return path.basename(filename || "generated_file").replace(/[\\/:*?"<>|]/g, "_");
}

async function uniqueFilePath(directory, filename) {
  const parsed = path.parse(safeFilename(filename));
  let candidate = path.join(directory, `${parsed.name}${parsed.ext}`);
  let index = 1;
  while (true) {
    try {
      await fs.access(candidate);
      candidate = path.join(directory, `${parsed.name}-${index}${parsed.ext}`);
      index += 1;
    } catch {
      return candidate;
    }
  }
}

async function downloadsDirectory() {
  const directory = path.join(app.getPath("downloads"), "企业内部工作台");
  await ensureDirectory(directory);
  return directory;
}

ipcMain.handle("conversation:load", async (_event, payload) => {
  return createConversationStore(app.getPath("userData")).load(payload?.userId);
});

ipcMain.handle("conversation:save", async (_event, payload) => {
  return createConversationStore(app.getPath("userData")).save(payload?.userId, payload?.items);
});

ipcMain.handle("clipboard:write", async (_event, text) => {
  clipboard.writeText(String(text ?? ""));
  return true;
});

ipcMain.handle("file:download", async (_event, payload) => {
  const response = await fetch(payload.url, {
    method: "GET",
    headers: payload.headers || {},
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  const disposition = response.headers.get("content-disposition") || "";
  const filename = safeFilename(parseDownloadFilename(disposition, payload.filename || "generated_file"));
  const directory = await downloadsDirectory();
  const filePath = await uniqueFilePath(directory, filename);
  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.writeFile(filePath, buffer);

  return {
    filename,
    path: filePath,
  };
});

ipcMain.handle("file:saveBase64", async (_event, payload) => {
  const filename = safeFilename(payload.filename || "generated_file");
  const directory = await downloadsDirectory();
  const filePath = await uniqueFilePath(directory, filename);
  await fs.writeFile(filePath, Buffer.from(payload.contentBase64 || "", "base64"));

  return {
    filename,
    path: filePath,
  };
});

ipcMain.handle("file:openPath", async (_event, filePath) => {
  return shell.openPath(String(filePath || ""));
});
