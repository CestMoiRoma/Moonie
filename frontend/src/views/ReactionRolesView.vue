<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { api, type Channel, type ReactionRoleMessage, type Role } from "../api/client";

const props = defineProps<{ guildId: string }>();

const messages = ref<ReactionRoleMessage[]>([]);
const channels = ref<Channel[]>([]);
const roles = ref<Role[]>([]);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const draft = reactive({
  channel_id: "",
  mode: "emoji" as "emoji" | "button",
  title: "",
  description: "",
  entries: [] as { role_id: string; emoji: string; label: string }[],
});

function roleName(id: string) {
  return roles.value.find((r) => r.id === id)?.name ?? id;
}
function channelName(id: string) {
  const c = channels.value.find((c) => c.id === id);
  return c ? `#${c.name}` : id;
}

async function load() {
  toast.value = null;
  const [msgs, chs, rls] = await Promise.all([
    api.reactionRoles(props.guildId),
    api.channels(props.guildId),
    api.roles(props.guildId),
  ]);
  messages.value = msgs;
  channels.value = chs.filter((c) => c.type === "text");
  roles.value = rls;
}

function addEntry() {
  draft.entries.push({ role_id: roles.value[0]?.id ?? "", emoji: "", label: "" });
}
function removeEntry(i: number) {
  draft.entries.splice(i, 1);
}

async function create() {
  if (!draft.channel_id || draft.entries.length === 0) {
    toast.value = { kind: "err", text: "Pick a channel and add at least one entry." };
    return;
  }
  try {
    await api.createReactionRole(props.guildId, {
      channel_id: Number(draft.channel_id),
      mode: draft.mode,
      title: draft.title || null,
      description: draft.description || null,
      entries: draft.entries.map((e) => ({
        role_id: Number(e.role_id),
        emoji: e.emoji || null,
        label: e.label || null,
      })),
    });
    toast.value = { kind: "ok", text: "Reaction-role message created. Publish it to post." };
    draft.entries = [];
    draft.title = "";
    draft.description = "";
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function publish(id: number) {
  toast.value = null;
  try {
    await api.publishReactionRole(props.guildId, id);
    toast.value = { kind: "ok", text: "Published to the channel." };
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function remove(id: number) {
  await api.deleteReactionRole(props.guildId, id);
  await load();
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Reaction Roles</h2>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>New message</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 200px">
        <label>Channel</label>
        <select v-model="draft.channel_id">
          <option value="">— Select —</option>
          <option v-for="c in channels" :key="c.id" :value="c.id">#{{ c.name }}</option>
        </select>
      </div>
      <div class="field" style="flex: 0 0 160px">
        <label>Mode</label>
        <select v-model="draft.mode">
          <option value="emoji">Emoji reactions</option>
          <option value="button">Buttons</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label>Title</label>
      <input v-model="draft.title" placeholder="Pick your roles" />
    </div>
    <div class="field">
      <label>Description (optional — auto-generated from entries if blank)</label>
      <textarea v-model="draft.description" rows="2"></textarea>
    </div>

    <label class="muted">Entries</label>
    <div v-for="(e, i) in draft.entries" :key="i" class="row entry">
      <div class="field" style="flex: 1 1 160px">
        <select v-model="e.role_id">
          <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
      <div v-if="draft.mode === 'emoji'" class="field" style="flex: 0 0 110px">
        <input v-model="e.emoji" placeholder="😀 or <:n:id>" />
      </div>
      <div v-else class="field" style="flex: 1 1 120px">
        <input v-model="e.label" placeholder="Button label" />
      </div>
      <button class="danger" @click="removeEntry(i)">✕</button>
    </div>
    <div class="row">
      <button @click="addEntry">+ Add entry</button>
      <button class="primary" @click="create">Create</button>
    </div>
  </div>

  <div class="card">
    <h3>Existing messages</h3>
    <p v-if="!messages.length" class="muted">None yet.</p>
    <div v-for="m in messages" :key="m.id" class="rr-item">
      <div>
        <strong>{{ m.title || "(untitled)" }}</strong>
        <span class="pill">{{ m.mode }}</span>
        <span class="pill">{{ channelName(m.channel_id) }}</span>
        <span v-if="m.message_id" class="pill">published</span>
        <div class="muted">
          {{ m.entries.map((e) => roleName(e.role_id)).join(", ") }}
        </div>
      </div>
      <div class="row">
        <button class="primary" @click="publish(m.id)">
          {{ m.message_id ? "Re-publish" : "Publish" }}
        </button>
        <button class="danger" @click="remove(m.id)">Delete</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.entry {
  margin-bottom: 8px;
}
.rr-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.rr-item:last-child {
  border-bottom: none;
}
</style>
