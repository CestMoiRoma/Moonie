<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { api, type Channel, type FormSubmission, type FormTemplate } from "../api/client";

const props = defineProps<{ guildId: string }>();

const forms = ref<FormTemplate[]>([]);
const channels = ref<Channel[]>([]);
const editingId = ref<number | null>(null);
const submissions = ref<FormSubmission[]>([]);
const submissionsFor = ref<string | null>(null);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const form = reactive({
  name: "",
  title: "",
  submit_channel_id: "",
  fields: [] as { label: string; style: string; required: boolean; placeholder: string }[],
});

async function load() {
  const [fs, chs] = await Promise.all([api.forms(props.guildId), api.channels(props.guildId)]);
  forms.value = fs;
  channels.value = chs.filter((c) => c.type === "text");
}

function reset() {
  editingId.value = null;
  form.name = "";
  form.title = "";
  form.submit_channel_id = "";
  form.fields = [];
}

function edit(f: FormTemplate) {
  editingId.value = f.id;
  form.name = f.name;
  form.title = f.title;
  form.submit_channel_id = f.submit_channel_id ?? "";
  form.fields = f.fields.map((fl) => ({
    label: fl.label,
    style: fl.style,
    required: fl.required,
    placeholder: fl.placeholder ?? "",
  }));
}

function addField() {
  if (form.fields.length >= 5) {
    toast.value = { kind: "err", text: "Discord modals allow at most 5 fields." };
    return;
  }
  form.fields.push({ label: "", style: "short", required: true, placeholder: "" });
}

async function save() {
  if (!form.name || !form.title || form.fields.length === 0) {
    toast.value = { kind: "err", text: "Name, title, and at least one field are required." };
    return;
  }
  const body = {
    name: form.name,
    title: form.title,
    submit_channel_id: form.submit_channel_id ? Number(form.submit_channel_id) : null,
    fields: form.fields.map((f) => ({
      label: f.label,
      style: f.style,
      required: f.required,
      placeholder: f.placeholder || null,
    })),
  };
  try {
    if (editingId.value) await api.updateForm(props.guildId, editingId.value, body);
    else await api.createForm(props.guildId, body);
    toast.value = { kind: "ok", text: "Form saved. Members open it with /form." };
    reset();
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function remove(id: number) {
  await api.deleteForm(props.guildId, id);
  if (editingId.value === id) reset();
  if (submissionsFor.value && Number(submissionsFor.value) === id) submissionsFor.value = null;
  await load();
}

async function viewSubmissions(f: FormTemplate) {
  submissionsFor.value = String(f.id);
  submissions.value = await api.submissions(props.guildId, f.id);
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Custom Forms</h2>
  <p class="muted">
    Build a form here; members fill it in via the <strong>/form</strong> slash command (a Discord
    modal). Submissions are stored and posted to the form's channel.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>{{ editingId ? "Edit form" : "New form" }}</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 180px">
        <label>Name (used in /form)</label>
        <input v-model="form.name" placeholder="apply" />
      </div>
      <div class="field" style="flex: 1 1 180px">
        <label>Modal title (max 45)</label>
        <input v-model="form.title" maxlength="45" placeholder="Staff Application" />
      </div>
    </div>
    <div class="field" style="max-width: 280px">
      <label>Post submissions to</label>
      <select v-model="form.submit_channel_id">
        <option value="">— Don't post —</option>
        <option v-for="c in channels" :key="c.id" :value="c.id">#{{ c.name }}</option>
      </select>
    </div>

    <label class="muted">Fields (max 5)</label>
    <div v-for="(f, i) in form.fields" :key="i" class="row entry">
      <div class="field" style="flex: 1 1 150px">
        <input v-model="f.label" maxlength="45" placeholder="Question label" />
      </div>
      <div class="field" style="flex: 0 0 120px">
        <select v-model="f.style">
          <option value="short">Short</option>
          <option value="paragraph">Paragraph</option>
        </select>
      </div>
      <div class="field" style="flex: 1 1 140px">
        <input v-model="f.placeholder" maxlength="100" placeholder="Placeholder" />
      </div>
      <label class="inline"><input type="checkbox" v-model="f.required" /> required</label>
      <button class="danger" @click="form.fields.splice(i, 1)">✕</button>
    </div>
    <div class="row">
      <button @click="addField">+ Add field</button>
      <button class="primary" @click="save">{{ editingId ? "Update" : "Create" }}</button>
      <button v-if="editingId" @click="reset">Cancel</button>
    </div>
  </div>

  <div class="card">
    <h3>Forms</h3>
    <p v-if="!forms.length" class="muted">None yet.</p>
    <div v-for="f in forms" :key="f.id" class="item">
      <div>
        <strong>/form {{ f.name }}</strong> — {{ f.title }}
        <div class="muted">{{ f.fields.length }} field(s)</div>
      </div>
      <div class="row">
        <button @click="viewSubmissions(f)">Submissions</button>
        <button @click="edit(f)">Edit</button>
        <button class="danger" @click="remove(f.id)">Delete</button>
      </div>
    </div>
  </div>

  <div v-if="submissionsFor" class="card">
    <h3>Submissions</h3>
    <p v-if="!submissions.length" class="muted">No submissions yet.</p>
    <div v-for="s in submissions" :key="s.id" class="sub">
      <div class="muted">user {{ s.user_id }} · {{ new Date(s.created_at).toLocaleString() }}</div>
      <div v-for="(val, key) in s.answers" :key="key">
        <strong>{{ key }}:</strong> {{ val }}
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
.sub {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
</style>
