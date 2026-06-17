<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { api, type ApiKey, type Guild } from "../api/client";
import { guildState } from "../store/guild";

// API keys are global (not per-guild), but a key can optionally be restricted to
// one guild. We keep the guildId prop for a consistent page signature.
defineProps<{ guildId: string }>();

const keys = ref<ApiKey[]>([]);
const scopes = ref<string[]>([]);
const guilds = ref<readonly Guild[]>([]);
const newKey = ref<string | null>(null); // plaintext, shown once
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const form = reactive({
  name: "",
  scopes: [] as string[],
  guild_id: "",
});

function guildName(id: string | null) {
  if (!id) return "All guilds";
  return guilds.value.find((g) => g.id === id)?.name ?? id;
}

async function load() {
  const [ks, ss] = await Promise.all([api.apiKeys(), api.apiKeyScopes()]);
  keys.value = ks;
  scopes.value = ss;
  guilds.value = guildState.guilds;
}

async function create() {
  if (!form.name || form.scopes.length === 0) {
    toast.value = { kind: "err", text: "Name and at least one scope are required." };
    return;
  }
  try {
    const created = await api.createApiKey({
      name: form.name,
      scopes: form.scopes,
      guild_id: form.guild_id ? Number(form.guild_id) : null,
    });
    newKey.value = created.key;
    toast.value = { kind: "ok", text: "Key created — copy it now, it won't be shown again." };
    form.name = "";
    form.scopes = [];
    form.guild_id = "";
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function toggle(k: ApiKey) {
  await api.updateApiKey(k.id, { enabled: !k.enabled });
  await load();
}

async function revoke(id: number) {
  await api.deleteApiKey(id);
  await load();
}

async function copyKey() {
  if (!newKey.value) return;
  try {
    await navigator.clipboard.writeText(newKey.value);
    toast.value = { kind: "ok", text: "Copied to clipboard." };
  } catch {
    toast.value = { kind: "err", text: "Clipboard unavailable — copy it manually." };
  }
}

function fmt(ts: string | null) {
  return ts ? new Date(ts).toLocaleString() : "never";
}

onMounted(load);
</script>

<template>
  <h2>External API Keys</h2>
  <p class="muted">
    Keys for the <strong>external HTTP API</strong> (<code>/external/v1</code>, docs at
    <code>/external/docs</code>). Give each integration its own key with only the scopes it needs.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div v-if="newKey" class="card newkey">
    <h3>🔑 New key — copy it now</h3>
    <p class="muted">This is the only time the full key is shown.</p>
    <code class="keyval">{{ newKey }}</code>
    <div class="row">
      <button class="primary" @click="copyKey">Copy</button>
      <button @click="newKey = null">Done</button>
    </div>
  </div>

  <div class="card">
    <h3>Create a key</h3>
    <div class="field">
      <label>Name / integration</label>
      <input v-model="form.name" placeholder="my-website" />
    </div>
    <div class="field">
      <label>Scopes</label>
      <label v-for="s in scopes" :key="s" class="inline">
        <input type="checkbox" :value="s" v-model="form.scopes" /> {{ s }}
      </label>
    </div>
    <div class="field" style="max-width: 280px">
      <label>Restrict to guild (optional)</label>
      <select v-model="form.guild_id">
        <option value="">All guilds</option>
        <option v-for="g in guilds" :key="g.id" :value="g.id">{{ g.name }}</option>
      </select>
    </div>
    <button class="primary" @click="create">Create key</button>
  </div>

  <div class="card">
    <h3>Keys</h3>
    <table v-if="keys.length">
      <thead>
        <tr><th>Name</th><th>Prefix</th><th>Scopes</th><th>Guild</th><th>Last used</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="k in keys" :key="k.id" :class="{ disabled: !k.enabled }">
          <td>{{ k.name }}</td>
          <td><code>{{ k.key_prefix }}…</code></td>
          <td>
            <span v-for="s in k.scopes" :key="s" class="pill">{{ s }}</span>
          </td>
          <td class="muted">{{ guildName(k.guild_id) }}</td>
          <td class="muted">{{ fmt(k.last_used_at) }}</td>
          <td class="row">
            <button @click="toggle(k)">{{ k.enabled ? "Disable" : "Enable" }}</button>
            <button class="danger" @click="revoke(k.id)">Revoke</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">No keys yet.</p>
  </div>
</template>

<style scoped>
.newkey {
  border-color: var(--accent);
}
.keyval {
  display: block;
  background: var(--bg-elev2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  margin: 10px 0;
  word-break: break-all;
  font-size: 13px;
}
.inline {
  color: var(--text-dim);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-right: 16px;
}
.inline input {
  width: auto;
}
tr.disabled td {
  opacity: 0.5;
}
.pill {
  margin-right: 4px;
}
</style>
