<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { api, type Channel, type EmbedTemplate } from "../api/client";

const props = defineProps<{ guildId: string }>();

const embeds = ref<EmbedTemplate[]>([]);
const channels = ref<Channel[]>([]);
const sendChannel = ref<string>("");
const editingId = ref<number | null>(null);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const form = reactive({
  name: "",
  title: "",
  description: "",
  color: "#7c5cff",
  footer: "",
  image_url: "",
  thumbnail_url: "",
  fields: [] as { name: string; value: string; inline: boolean }[],
});

const previewColor = computed(() => form.color || "#2a2f3c");

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    name: "",
    title: "",
    description: "",
    color: "#7c5cff",
    footer: "",
    image_url: "",
    thumbnail_url: "",
    fields: [],
  });
}

function hexToInt(hex: string): number | null {
  const m = hex.replace("#", "");
  return m ? parseInt(m, 16) : null;
}
function intToHex(n: number | null): string {
  if (n === null || n === undefined) return "#7c5cff";
  return "#" + n.toString(16).padStart(6, "0");
}

async function load() {
  const [es, chs] = await Promise.all([api.embeds(props.guildId), api.channels(props.guildId)]);
  embeds.value = es;
  channels.value = chs.filter((c) => c.type === "text");
}

function edit(e: EmbedTemplate) {
  editingId.value = e.id;
  Object.assign(form, {
    name: e.name,
    title: e.title ?? "",
    description: e.description ?? "",
    color: intToHex(e.color),
    footer: e.footer ?? "",
    image_url: e.image_url ?? "",
    thumbnail_url: e.thumbnail_url ?? "",
    fields: e.fields.map((f) => ({ ...f })),
  });
}

function addField() {
  form.fields.push({ name: "", value: "", inline: false });
}

async function save() {
  if (!form.name) {
    toast.value = { kind: "err", text: "Give the template a name." };
    return;
  }
  const body = {
    name: form.name,
    title: form.title || null,
    description: form.description || null,
    color: hexToInt(form.color),
    footer: form.footer || null,
    image_url: form.image_url || null,
    thumbnail_url: form.thumbnail_url || null,
    fields: form.fields.filter((f) => f.name && f.value),
  };
  try {
    if (editingId.value) await api.updateEmbed(props.guildId, editingId.value, body);
    else await api.createEmbed(props.guildId, body);
    toast.value = { kind: "ok", text: "Embed saved." };
    resetForm();
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function send(id: number) {
  if (!sendChannel.value) {
    toast.value = { kind: "err", text: "Pick a channel to send to." };
    return;
  }
  try {
    await api.sendEmbed(props.guildId, id, sendChannel.value);
    toast.value = { kind: "ok", text: "Embed sent." };
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function remove(id: number) {
  await api.deleteEmbed(props.guildId, id);
  if (editingId.value === id) resetForm();
  await load();
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Embed Builder</h2>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>{{ editingId ? "Edit embed" : "New embed" }}</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 200px">
        <label>Template name</label>
        <input v-model="form.name" placeholder="rules-embed" />
      </div>
      <div class="field" style="flex: 0 0 120px">
        <label>Color</label>
        <input v-model="form.color" type="color" />
      </div>
    </div>
    <div class="field">
      <label>Title</label>
      <input v-model="form.title" />
    </div>
    <div class="field">
      <label>Description</label>
      <textarea v-model="form.description" rows="3"></textarea>
    </div>

    <label class="muted">Fields</label>
    <div v-for="(f, i) in form.fields" :key="i" class="row entry">
      <div class="field" style="flex: 1 1 120px"><input v-model="f.name" placeholder="Name" /></div>
      <div class="field" style="flex: 2 1 200px"><input v-model="f.value" placeholder="Value" /></div>
      <label class="inline"><input type="checkbox" v-model="f.inline" /> inline</label>
    </div>
    <button @click="addField">+ Add field</button>

    <div class="row" style="margin-top: 12px">
      <div class="field" style="flex: 1 1 160px">
        <label>Footer</label>
        <input v-model="form.footer" />
      </div>
      <div class="field" style="flex: 1 1 160px">
        <label>Thumbnail URL</label>
        <input v-model="form.thumbnail_url" />
      </div>
      <div class="field" style="flex: 1 1 160px">
        <label>Image URL</label>
        <input v-model="form.image_url" />
      </div>
    </div>

    <div class="preview" :style="{ borderLeftColor: previewColor }">
      <strong>{{ form.title || "(no title)" }}</strong>
      <p class="muted" style="white-space: pre-wrap">{{ form.description }}</p>
    </div>

    <div class="row">
      <button class="primary" @click="save">{{ editingId ? "Update" : "Create" }}</button>
      <button v-if="editingId" @click="resetForm">Cancel</button>
    </div>
  </div>

  <div class="card">
    <h3>Saved embeds</h3>
    <div class="field" style="max-width: 280px">
      <label>Send to channel</label>
      <select v-model="sendChannel">
        <option value="">— Select —</option>
        <option v-for="c in channels" :key="c.id" :value="c.id">#{{ c.name }}</option>
      </select>
    </div>
    <p v-if="!embeds.length" class="muted">No saved embeds yet.</p>
    <div v-for="e in embeds" :key="e.id" class="rr-item">
      <div>
        <strong>{{ e.name }}</strong>
        <span class="muted">{{ e.title }}</span>
      </div>
      <div class="row">
        <button @click="edit(e)">Edit</button>
        <button class="primary" @click="send(e.id)">Send</button>
        <button class="danger" @click="remove(e.id)">Delete</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.entry {
  margin-bottom: 8px;
  align-items: center;
}
.inline {
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 4px;
}
.inline input {
  width: auto;
}
.preview {
  background: var(--bg-elev2);
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent);
  border-radius: 6px;
  padding: 12px 14px;
  margin: 14px 0;
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
