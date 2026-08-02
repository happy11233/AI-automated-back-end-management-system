const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("enterpriseBridge", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  maximize: () => ipcRenderer.invoke("window:maximize"),
  close: () => ipcRenderer.invoke("window:close"),
  apiRequest: (payload) => ipcRenderer.invoke("api:request", payload),
  abortApiStream: (requestId) => ipcRenderer.send("api:stream:abort", { requestId }),
  apiStream: async (payload, onChunk) => {
    const channel = `api:stream:${Date.now()}:${Math.random().toString(16).slice(2)}`;
    let streamClosed = false;
    let resolveStreamClose = () => {};
    const streamClosePromise = new Promise((resolve) => {
      resolveStreamClose = resolve;
    });
    const listener = (_event, item) => {
      if (item && typeof item.chunk === "string") {
        onChunk(item.chunk);
      }
      if (item?.done) {
        streamClosed = true;
        resolveStreamClose();
      }
    };
    ipcRenderer.on(channel, listener);
    try {
      const response = await ipcRenderer.invoke("api:stream", {
        ...payload,
        channel,
      });
      if (!streamClosed) {
        await Promise.race([
          streamClosePromise,
          new Promise((resolve) => setTimeout(resolve, 250)),
        ]);
      }
      return response;
    } finally {
      ipcRenderer.removeListener(channel, listener);
    }
  },
  loadConversations: (payload) => ipcRenderer.invoke("conversation:load", payload),
  saveConversations: (payload) => ipcRenderer.invoke("conversation:save", payload),
  copyText: (text) => ipcRenderer.invoke("clipboard:write", text),
  downloadFile: (payload) => ipcRenderer.invoke("file:download", payload),
  saveBase64File: (payload) => ipcRenderer.invoke("file:saveBase64", payload),
  openPath: (filePath) => ipcRenderer.invoke("file:openPath", filePath),
});
