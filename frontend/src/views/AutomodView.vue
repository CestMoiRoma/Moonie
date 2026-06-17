<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { api, type AutomodRule } from "../api/client";

const props = defineProps<{ guildId: string }>();

const rules = ref<AutomodRule[]>([]);
const editingId = ref<number | null>(null);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const form = reactive({
  name: "",
  kind: "word" as "word" | "link" | "regex",
  pattern: "",
  action: "delete" as "delete" | "warn",
  enabled: true,
});

const HINTS: Record<string, string> = {
  word: "Matches the whole word, case-insensitive.",
  link: "Empty = block all links; otherwise blocks links containing this text (e.g. a domain).",
  regex: "Python regular expression, case-insensitive.",
};

async function load() {
  rules.value = await api.automodRules(props.guildId);
}

function reset() {
  editingId.value = null;
  form.name = "";
  form.kind = "word";
  form.pattern = "";
  form.action = "delete";
  form.enabled = true;
}

function edit(r: AutomodRule) {
  editingId.value = r.id;
  form.name = r.name;
  form.kind = r.kind;
  form.pattern = r.pattern;
  form.action = r.action;
  form.enabled = r.enabled;
}

async function save() {
  if (!form.name || (form.kind !== "link" && !form.pattern)) {
    toast.value = { kind: "err", text: "Name and pattern are required (except 'link' allows empty)." };
    return;
  }
  const body = { ...form };
  try {
    if (editingId.value) await api.updateAutomodRule(props.guildId, editingId.value, body);
    else await api.createAutomodRule(props.guildId, body);
    toast.value = { kind: "ok", text: "Rule saved." };
    reset();
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function toggle(r: AutomodRule) {
  await api.updateAutomodRule(props.guildId, r.id, { ...r, enabled: !r.enabled });
  await load();
}

async function remove(id: number) {
  await api.deleteAutomodRule(props.guildId, id);
  if (editingId.value === id) reset();
  await load();
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Automod</h2>
  <p class="muted">
    Automatically delete messages matching a rule. Members who can manage messages are exempt;
    deletions are recorded in the moderation audit log.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>{{ editingId ? "Edit rule" : "New rule" }}</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 160px">
        <label>Name</label>
        <input v-model="form.name" placeholder="no-invites" />
      </div>
      <div class="field" style="flex: 0 0 130px">
        <label>Type</label>
        <select v-model="form.kind">
          <option value="word">Word</option>
          <option value="link">Link</option>
          <option value="regex">Regex</option>
        </select>
      </div>
      <div class="field" style="flex: 0 0 130px">
        <label>Action</label>
        <select v-model="form.action">
          <option value="delete">Delete</option>
          <option value="warn">Delete + warn</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label>Pattern</label>
      <input v-model="form.pattern" :placeholder="form.kind === 'link' ? 'discord.gg (or leave blank for all links)' : ''" />
      <small class="muted">{{ HINTS[form.kind] }}</small>
    </div>
    <label class="inline"><input type="checkbox" v-model="form.enabled" /> enabled</label>
    <div class="row" style="margin-top: 10px">
      <button class="primary" @click="save">{{ editingId ? "Update" : "Create" }}</button>
      <button v-if="editingId" @click="reset">Cancel</button>
    </div>
  </div>

  <div class="card">
    <h3>Rules</h3>
    <p v-if="!rules.length" class="muted">No rules yet.</p>
    <div v-for="r in rules" :key="r.id" class="item">
      <div>
        <strong>{{ r.name }}</strong>
        <span class="pill">{{ r.kind }}</span>
        <span class="pill">{{ r.action }}</span>
        <span class="pill" :style="{ borderColor: r.enabled ? 'var(--ok)' : 'var(--border)' }">
          {{ r.enabled ? "on" : "off" }}
        </span>
        <div class="muted">{{ r.pattern || "(any link)" }}</div>
      </div>
      <div class="row">
        <button @click="toggle(r)">{{ r.enabled ? "Disable" : "Enable" }}</button>
        <button @click="edit(r)">Edit</button>
        <button class="danger" @click="remove(r.id)">Delete</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inline {
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 4px;
}
.inline input {
  width: auto;
}
small {
  display: block;
  margin-top: 4px;
}
.item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.item:last-child {
  border-bottom: none;
}
</style>
