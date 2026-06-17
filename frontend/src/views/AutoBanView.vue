<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type GlobalBan } from "../api/client";

// Auto-ban is a global list (not per-guild), but we keep the guildId prop for
// a consistent page signature.
defineProps<{ guildId: string }>();

const bans = ref<GlobalBan[]>([]);
const newId = ref("");
const newReason = ref("");
const importText = ref("");
const importReason = ref("");
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

async function load() {
  bans.value = await api.bans();
}

async function add() {
  if (!newId.value) {
    toast.value = { kind: "err", text: "Enter a user id." };
    return;
  }
  try {
    await api.addBan(Number(newId.value), newReason.value || null);
    toast.value = { kind: "ok", text: "Added to the ban database." };
    newId.value = "";
    newReason.value = "";
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function remove(userId: string) {
  await api.removeBan(userId);
  await load();
}

async function runImport() {
  const ids = importText.value
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isFinite(n));
  if (!ids.length) {
    toast.value = { kind: "err", text: "No valid ids found." };
    return;
  }
  try {
    const res = await api.importBans(ids, importReason.value || null);
    toast.value = { kind: "ok", text: `Imported ${res.added}, skipped ${res.skipped}.` };
    importText.value = "";
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function exportList() {
  const text = bans.value.map((b) => b.user_id).join("\n");
  try {
    await navigator.clipboard.writeText(text);
    toast.value = { kind: "ok", text: `Copied ${bans.value.length} ids to clipboard.` };
  } catch {
    toast.value = { kind: "err", text: "Clipboard unavailable — select the ids manually." };
  }
}

function fmt(ts: string) {
  return new Date(ts).toLocaleDateString();
}

onMounted(load);
</script>

<template>
  <h2>Auto-Ban Database</h2>
  <p class="muted">
    Users in this list are automatically banned the moment they join any server the bot is in.
    This list is global across all guilds.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>Add a user</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 200px">
        <label>User id</label>
        <input v-model="newId" placeholder="123456789012345678" />
      </div>
      <div class="field" style="flex: 2 1 220px">
        <label>Reason</label>
        <input v-model="newReason" placeholder="Optional reason" />
      </div>
    </div>
    <button class="primary" @click="add">Add to banlist</button>
  </div>

  <div class="card">
    <h3>Bulk import / export</h3>
    <div class="field">
      <label>Paste user ids (comma, space, or newline separated)</label>
      <textarea v-model="importText" rows="3" placeholder="123, 456, 789"></textarea>
    </div>
    <div class="field" style="max-width: 320px">
      <label>Reason for imported ids</label>
      <input v-model="importReason" placeholder="Optional" />
    </div>
    <div class="row">
      <button class="primary" @click="runImport">Import</button>
      <button @click="exportList">Copy all ids</button>
    </div>
  </div>

  <div class="card">
    <h3>Banned users ({{ bans.length }})</h3>
    <table v-if="bans.length">
      <thead>
        <tr><th>User id</th><th>Reason</th><th>Added</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="b in bans" :key="b.user_id">
          <td>{{ b.user_id }}</td>
          <td>{{ b.reason ?? "—" }}</td>
          <td class="muted">{{ fmt(b.created_at) }}</td>
          <td><button class="danger" @click="remove(b.user_id)">Remove</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">The ban database is empty.</p>
  </div>
</template>
