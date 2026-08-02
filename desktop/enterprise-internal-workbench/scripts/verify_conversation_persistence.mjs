import { createRequire } from "node:module";
import { strict as assert } from "node:assert";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const require = createRequire(import.meta.url);
const { createConversationStore } = require("../electron/conversation_store.cjs");

function conversation(userId, id, updatedAt, threadId = `${id}-thread`) {
  return {
    id,
    userId,
    title: id,
    threadId,
    messages: [{ id: `${id}-message`, role: "user", content: "测试内容", createdAt: updatedAt }],
    createdAt: updatedAt,
    updatedAt,
  };
}

async function main() {
  const tempDirectory = await fs.mkdtemp(path.join(os.tmpdir(), "enterprise-workbench-"));
  try {
    const store = createConversationStore(tempDirectory);
    const userAItems = [
      conversation("user-a", "conversation-a-1", "2026-07-30T10:00:00.000Z"),
      conversation("user-a", "conversation-a-2", "2026-07-30T11:00:00.000Z"),
    ];
    const userBItems = [conversation("user-b", "conversation-b-1", "2026-07-30T12:00:00.000Z")];

    await store.save("user-a", userAItems);
    await store.save("user-b", userBItems);

    const loadedA = await createConversationStore(tempDirectory).load("user-a");
    const loadedB = await createConversationStore(tempDirectory).load("user-b");
    assert.deepEqual(loadedA.items.map((item) => item.id), ["conversation-a-2", "conversation-a-1"]);
    assert.deepEqual(loadedB.items.map((item) => item.id), ["conversation-b-1"]);
    assert.equal(loadedA.items[0].threadId, "conversation-a-2-thread");

    await assert.rejects(() => store.load("../user-a"), /无效的用户标识/);
    await assert.rejects(() => store.save("user/a", []), /无效的用户标识/);

    const legacyRoot = await fs.mkdtemp(path.join(os.tmpdir(), "enterprise-workbench-legacy-"));
    try {
      const legacyItems = [
        conversation("legacy-a", "legacy-a-1", "2026-07-29T10:00:00.000Z"),
        conversation("legacy-b", "legacy-b-1", "2026-07-29T11:00:00.000Z"),
      ];
      await fs.writeFile(
        path.join(legacyRoot, "conversations.json"),
        `${JSON.stringify(legacyItems)}\n`,
        "utf8",
      );

      const migrated = await createConversationStore(legacyRoot).load("legacy-a");
      assert.deepEqual(migrated.items.map((item) => item.id), ["legacy-a-1"]);
      assert.equal(await fs.access(path.join(legacyRoot, "conversations", "legacy-a.json")).then(() => true), true);
      assert.equal(await fs.access(path.join(legacyRoot, "conversations.json.legacy")).then(() => true), true);
      assert.equal(await fs.access(path.join(legacyRoot, "conversations.json.migrated")).then(() => true), true);
    } finally {
      await fs.rm(legacyRoot, { recursive: true, force: true });
    }

    const corruptRoot = await fs.mkdtemp(path.join(os.tmpdir(), "enterprise-workbench-corrupt-"));
    try {
      await fs.mkdir(path.join(corruptRoot, "conversations"), { recursive: true });
      await fs.writeFile(
        path.join(corruptRoot, "conversations", "user-c.json"),
        "{broken-json",
        "utf8",
      );
      const recovered = await createConversationStore(corruptRoot).load("user-c");
      assert.deepEqual(recovered.items, []);
    } finally {
      await fs.rm(corruptRoot, { recursive: true, force: true });
    }

    console.log(JSON.stringify({
      ok: true,
      user_partition_checked: true,
      restart_restore_checked: true,
      path_traversal_blocked: true,
      legacy_migration_checked: true,
      corrupt_file_recovery_checked: true,
      max_conversation_limit: 5,
    }, null, 2));
  } finally {
    await fs.rm(tempDirectory, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
