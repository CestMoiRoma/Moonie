<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api, type ModAction } from "../api/client";

const props = defineProps<{ guildId: string }>();

const actions = ref<ModAction[]>([]);
const action = ref("kick");
const targetId = ref("");
const reason = ref("");
const minutes = ref(60);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);
const busy = ref(false);

const ACTIONS = ["kick", "ban", "unban", "mute", "unmute", "warn"];

async function loadLog() {
  actions.value = await api.modActions(props.guildId);
}

async function submit() {
  if (!targetId.value) {
    toast.value = { kind: "err", text: "Target user id is required." };
    return;
  }
  busy.value = true;
  toast.value = null;
  try {
    await api.createModAction(props.guildId, {
      action: action.value,
      target_id: Number(targetId.value),
      reason: reason.value || null,
      duration_minutes: action.value === "mute" ? Number(minutes.value) : null,
    });
    toast.value = { kind: "ok", text: `Applied ${action.value}.` };
    targetId.value = "";
    reason.value = "";
    await loadLog();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  } finally {
    busy.value = false;
  }
}

function fmt(ts: string) {
  return new Date(ts).toLocaleString();
}

onMounted(loadLog);
watch(() => props.guildId, loadLog);
</script>

<template>
  <h2>Moderation</h2>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>Issue an action</h3>
    <div class="row">
      <div class="field" style="flex: 0 0 130px">
        <label>Action</label>
        <select v-model="action">
          <option v-for="a in ACTIONS" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>
      <div class="field" style="flex: 1 1 200px">
        <label>Target user id</label>
        <input v-model="targetId" placeholder="123456789012345678" />
      </div>
      <div v-if="action === 'mute'" class="field" style="flex: 0 0 110px">
        <label>Minutes</label>
        <input v-model.number="minutes" type="number" min="1" />
      </div>
    </div>
    <div class="field">
      <label>Reason</label>
      <input v-model="reason" placeholder="Optional reason" />
    </div>
    <button class="primary" :disabled="busy" @click="submit">Apply</button>
  </div>

  <div class="card">
    <h3>Audit log</h3>
    <table v-if="actions.length">
      <thead>
        <tr><th>When</th><th>Action</th><th>Target</th><th>By</th><th>Reason</th></tr>
      </thead>
      <tbody>
        <tr v-for="a in actions" :key="a.id">
          <td class="muted">{{ fmt(a.created_at) }}</td>
          <td><span class="pill">{{ a.action }}</span></td>
          <td>{{ a.target_tag ?? a.target_id }}</td>
          <td class="muted">{{ a.moderator_tag ?? a.moderator_id }}</td>
          <td>{{ a.reason ?? "—" }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">No moderation actions recorded yet.</p>
  </div>
</template>
