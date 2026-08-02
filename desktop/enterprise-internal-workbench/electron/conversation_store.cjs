const fs = require("fs/promises");
const path = require("path");

const MAX_CONVERSATIONS = 5;
const SAFE_USER_ID_PATTERN = /^[A-Za-z0-9_-]{1,160}$/;

function normalizeConversationUserId(userId) {
  const normalized = String(userId || "").trim();
  if (!SAFE_USER_ID_PATTERN.test(normalized)) {
    throw new Error("无效的用户标识");
  }
  return normalized;
}

function createConversationStore(userDataPath) {
  const rootPath = path.resolve(String(userDataPath || ""));

  function conversationsDirectory() {
    return path.join(rootPath, "conversations");
  }

  function conversationsPath(userId) {
    const safeUserId = normalizeConversationUserId(userId);
    return path.join(conversationsDirectory(), `${safeUserId}.json`);
  }

  function legacyConversationsPath() {
    return path.join(rootPath, "conversations.json");
  }

  function legacyMigrationMarkerPath() {
    return `${legacyConversationsPath()}.migrated`;
  }

  async function ensureDirectory(directory) {
    await fs.mkdir(directory, { recursive: true });
  }

  async function readJsonFile(filePath, fallback) {
    try {
      const content = await fs.readFile(filePath, "utf8");
      return JSON.parse(content);
    } catch {
      return fallback;
    }
  }

  async function writeJsonFile(filePath, value) {
    await ensureDirectory(path.dirname(filePath));
    const tempPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
    try {
      await fs.writeFile(tempPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
      await fs.rename(tempPath, filePath);
    } finally {
      await fs.rm(tempPath, { force: true }).catch(() => {});
    }
  }

  async function fileExists(filePath) {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  function normalizeConversationItems(value, userId) {
    const rawItems = Array.isArray(value)
      ? value
      : value && Array.isArray(value.items)
        ? value.items
        : [];

    return rawItems
      .filter((item) => (
        item
        && typeof item === "object"
        && String(item.userId || "") === userId
        && item.id
        && Array.isArray(item.messages)
      ))
      .sort((first, second) => (
        new Date(second.updatedAt || 0).getTime() - new Date(first.updatedAt || 0).getTime()
      ))
      .slice(0, MAX_CONVERSATIONS);
  }

  function conversationEnvelope(userId, items) {
    return {
      version: 1,
      user_id: userId,
      updated_at: new Date().toISOString(),
      items: normalizeConversationItems(items, userId),
    };
  }

  async function migrateLegacyConversations() {
    const legacyPath = legacyConversationsPath();
    if (!(await fileExists(legacyPath))) return;

    const legacy = await readJsonFile(legacyPath, null);
    if (!Array.isArray(legacy)) return;

    const grouped = new Map();
    for (const item of legacy) {
      const candidateUserId = String(item?.userId || "").trim();
      if (!SAFE_USER_ID_PATTERN.test(candidateUserId)) continue;
      const currentItems = grouped.get(candidateUserId) || [];
      currentItems.push(item);
      grouped.set(candidateUserId, currentItems);
    }

    for (const [userId, items] of grouped) {
      const targetPath = conversationsPath(userId);
      if (await fileExists(targetPath)) continue;
      await writeJsonFile(targetPath, conversationEnvelope(userId, items));
    }

    if (!(await fileExists(legacyMigrationMarkerPath()))) {
      await fs.copyFile(legacyPath, `${legacyPath}.legacy`).catch(() => {});
      await writeJsonFile(legacyMigrationMarkerPath(), {
        version: 1,
        migrated_at: new Date().toISOString(),
        users: [...grouped.keys()],
      });
    }
  }

  async function load(userId) {
    const safeUserId = normalizeConversationUserId(userId);
    await migrateLegacyConversations();
    const filePath = conversationsPath(safeUserId);
    const stored = await readJsonFile(filePath, null);
    return {
      path: filePath,
      items: normalizeConversationItems(stored, safeUserId),
    };
  }

  async function save(userId, items) {
    const safeUserId = normalizeConversationUserId(userId);
    const filePath = conversationsPath(safeUserId);
    await writeJsonFile(filePath, conversationEnvelope(safeUserId, items));
    return {
      ok: true,
      path: filePath,
    };
  }

  return {
    load,
    save,
    pathFor: conversationsPath,
  };
}

module.exports = {
  createConversationStore,
  normalizeConversationUserId,
};
