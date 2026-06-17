<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api, type FlaggedUser } from "../api/client";

const props = defineProps<{ guildId: string }>();

const flagged = ref<FlaggedUser[]>([]);
const userId = ref("");
const reason = ref("");
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

async function load() {
  flagged.value = await api.flagged(props.guildId);
}

async function flag() {
  if (!userId.value) {
    toast.value = { kind: "err", text: "Enter a user id." };
    return;
  }
  try {
    await api.flagUser(props.guildId, Number(userId.value), reason.value || null);
    toast.value = { kind: "ok", text: "User flagged — a log channel was created." };
    userId.value = "";
    reason.value = "";
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function unflag(uid: string) {
  await api.unflagUser(props.guildId, uid);
  await load();
}

function fmt(ts: string) {
  return new Date(ts).toLocaleDateString();
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Per-User Logging</h2>
  <p class="muted">
    Flag a suspicious user to create a dedicated private channel (under your configured logging
    category) that mirrors their messages — like a ticket, but for monitoring one user. Set the
    logging category in <strong>Welcome &amp; Roles → Settings</strong> first.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>Flag a user</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 200px">
        <label>User id</label>
        <input v-model="userId" placeholder="123456789012345678" />
      </div>
      <div class="field" style="flex: 2 1 220px">
        <label>Reason</label>
        <input v-model="reason" placeholder="Optional reason" />
      </div>
    </div>
    <button class="primary" @click="flag">Flag &amp; start logging</button>
  </div>

  <div class="card">
    <h3>Flagged users</h3>
    <table v-if="flagged.length">
      <thead>
        <tr><th>User id</th><th>Status</th><th>Reason</th><th>Since</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="f in flagged" :key="f.id">
          <td>{{ f.user_id }}</td>
          <td>
            <span class="pill" :style="{ borderColor: f.active ? 'var(--ok)' : 'var(--border)' }">
              {{ f.active ? "logging" : "stopped" }}
            </span>
          </td>
          <td>{{ f.reason ?? "—" }}</td>
          <td class="muted">{{ fmt(f.created_at) }}</td>
          <td>
            <button v-if="f.active" class="danger" @click="unflag(f.user_id)">Stop</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">No users are being logged.</p>
  </div>
</template>
