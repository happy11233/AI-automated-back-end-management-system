export {};

declare global {
  interface Window {
    enterpriseBridge?: {
      minimize: () => Promise<void>;
      maximize: () => Promise<boolean>;
      close: () => Promise<void>;
      apiRequest: (payload: DesktopApiRequest) => Promise<DesktopApiResponse>;
      abortApiStream: (requestId: string) => void;
      apiStream: (
        payload: DesktopApiRequest,
        onChunk: (chunk: string) => void,
      ) => Promise<DesktopApiResponse>;
      loadConversations: (payload: { userId: string }) => Promise<DesktopConversationStore>;
      saveConversations: (payload: { userId: string; items: unknown[] }) => Promise<{ ok: boolean; path: string }>;
      copyText: (text: string) => Promise<boolean>;
      downloadFile: (payload: DesktopDownloadRequest) => Promise<DesktopSavedFile>;
      saveBase64File: (payload: DesktopBase64FileRequest) => Promise<DesktopSavedFile>;
      openPath: (filePath: string) => Promise<string>;
    };
  }
}

type DesktopApiRequest = {
  url: string;
  method: string;
  headers: Record<string, string>;
  body?: string;
  requestId?: string;
};

type DesktopApiResponse = {
  ok: boolean;
  status: number;
  statusText: string;
  body: string;
};

type DesktopConversationStore = {
  path: string;
  items: unknown[];
};

type DesktopDownloadRequest = {
  url: string;
  headers: Record<string, string>;
  filename?: string;
};

type DesktopBase64FileRequest = {
  filename: string;
  mimeType?: string;
  contentBase64: string;
};

type DesktopSavedFile = {
  filename: string;
  path: string;
};
