<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { api, type CustomCommand, type EmbedTemplate } from "../api/client";

const props = defineProps<{ guildId: string }>();

const commands = ref<CustomCommand[]>([]);
const embeds = ref<EmbedTemplate[]>([]);
const editingId = ref<number | null>(null);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const prefix = "-"; // matches the bot's default PREFIX

const form = reactive({ name: "", response: "", embed_id: "" });

async function load() {
  const [cmds, es] = await Promise.all([
    api.customCommands(props.guildId),
    api.embeds(props.guildId),
  ]);
  commands.value = cmds;
  embeds.value = es;
}

function reset() {
  editingId.value = null;
  form.name = "";
  form.response = "";
  form.embed_id = "";
}

function edit(c: CustomCommand) {
  editingId.value = c.id;
  form.name = c.name;
  form.response = c.response;
  form.embed_id = c.embed_id ? String(c.embed_id) : "";
}

async function save() {
  if (!form.name || (!form.response && !form.embed_id)) {
    toast.value = { kind: "err", text: "Name and a response (text or embed) are required." };
    return;
  }
  const body = {
    name: form.name,
    response: form.response,
    embed_id: form.embed_id ? Number(form.embed_id) : null,
  };
  try {
    if (editingId.value) await api.updateCustomCommand(props.guildId, editingId.value, body);
    else await api.createCustomCommand(props.guildId, body);
    toast.value = { kind: "ok", text: "Command saved." };
    reset();
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function remove(id: number) {
  await api.deleteCustomCommand(props.guildId, id);
  if (editingId.value === id) reset();
  await load();
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Custom Commands</h2>
  <p class="muted">
    Members trigger these by typing <strong>{{ prefix }}name</strong> in chat. A command can reply
    with text, a saved embed, or both.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>{{ editingId ? "Edit command" : "New command" }}</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 160px">
        <label>Name (without prefix)</label>
        <input v-model="form.name" placeholder="rules" />
      </div>
      <div class="field" style="flex: 1 1 160px">
        <label>Attach a saved embed (optional)</label>
        <select v-model="form.embed_id">
          <option value="">— None —</option>
          <option v-for="e in embeds" :key="e.id" :value="String(e.id)">{{ e.name }}</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label>Response text</label>
      <textarea v-model="form.response" rows="3" placeholder="Be sure to read the rules!"></textarea>
    </div>
    <div class="row">
      <button class="primary" @click="save">{{ editingId ? "Update" : "Create" }}</button>
      <button v-if="editingId" @click="reset">Cancel</button>
    </div>
  </div>

  <div class="card">
    <h3>Commands</h3>
    <p v-if="!commands.length" class="muted">None yet.</p>
    <div v-for="c in commands" :key="c.id" class="item">
      <div>
        <strong>{{ prefix }}{{ c.name }}</strong>
        <span v-if="c.embed_id" class="pill">embed</span>
        <div class="muted">{{ c.response || "(embed only)" }}</div>
      </div>
      <div class="row">
        <button @click="edit(c)">Edit</button>
        <button class="danger" @click="remove(c.id)">Delete</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
