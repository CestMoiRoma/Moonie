<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { api, type Channel, type Group, type Role } from "../api/client";

const props = defineProps<{ guildId: string }>();

const groups = ref<Group[]>([]);
const roles = ref<Role[]>([]);
const channels = ref<Channel[]>([]);
const editingId = ref<number | null>(null);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const form = reactive({
  name: "",
  description: "",
  roleIds: [] as string[],
  channelIds: [] as string[],
});

function roleName(id: string) {
  return roles.value.find((r) => r.id === id)?.name ?? id;
}
function channelName(id: string) {
  const c = channels.value.find((c) => c.id === id);
  return c ? `#${c.name}` : id;
}

async function load() {
  const [gs, rls, chs] = await Promise.all([
    api.groups(props.guildId),
    api.roles(props.guildId),
    api.channels(props.guildId),
  ]);
  groups.value = gs;
  roles.value = rls;
  channels.value = chs.filter((c) => c.type === "text" || c.type === "voice");
}

function reset() {
  editingId.value = null;
  form.name = "";
  form.description = "";
  form.roleIds = [];
  form.channelIds = [];
}

function edit(g: Group) {
  editingId.value = g.id;
  form.name = g.name;
  form.description = g.description ?? "";
  form.roleIds = g.items.filter((i) => i.kind === "role").map((i) => i.discord_id);
  form.channelIds = g.items.filter((i) => i.kind === "channel").map((i) => i.discord_id);
}

async function save() {
  if (!form.name) {
    toast.value = { kind: "err", text: "Group needs a name." };
    return;
  }
  const items = [
    ...form.roleIds.map((id) => ({ kind: "role", discord_id: Number(id) })),
    ...form.channelIds.map((id) => ({ kind: "channel", discord_id: Number(id) })),
  ];
  const body = { name: form.name, description: form.description || null, items };
  try {
    if (editingId.value) await api.updateGroup(props.guildId, editingId.value, body);
    else await api.createGroup(props.guildId, body);
    toast.value = { kind: "ok", text: "Group saved." };
    reset();
    await load();
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function remove(id: number) {
  await api.deleteGroup(props.guildId, id);
  if (editingId.value === id) reset();
  await load();
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Groups</h2>
  <p class="muted">
    Bundle roles and channels under a name, then target the whole group in Bulk Permissions.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>{{ editingId ? "Edit group" : "New group" }}</h3>
    <div class="field">
      <label>Name</label>
      <input v-model="form.name" placeholder="staff-areas" />
    </div>
    <div class="field">
      <label>Description</label>
      <input v-model="form.description" />
    </div>
    <div class="row">
      <div class="field" style="flex: 1 1 200px">
        <label>Roles</label>
        <select v-model="form.roleIds" multiple size="6">
          <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
      <div class="field" style="flex: 1 1 200px">
        <label>Channels</label>
        <select v-model="form.channelIds" multiple size="6">
          <option v-for="c in channels" :key="c.id" :value="c.id">#{{ c.name }}</option>
        </select>
      </div>
    </div>
    <div class="row">
      <button class="primary" @click="save">{{ editingId ? "Update" : "Create" }}</button>
      <button v-if="editingId" @click="reset">Cancel</button>
    </div>
  </div>

  <div class="card">
    <h3>Existing groups</h3>
    <p v-if="!groups.length" class="muted">None yet.</p>
    <div v-for="g in groups" :key="g.id" class="item">
      <div>
        <strong>{{ g.name }}</strong>
        <span class="muted">{{ g.description }}</span>
        <div class="muted">
          {{ g.items.filter((i) => i.kind === "role").length }} roles,
          {{ g.items.filter((i) => i.kind === "channel").length }} channels —
          {{
            g.items
              .map((i) => (i.kind === "role" ? roleName(i.discord_id) : channelName(i.discord_id)))
              .join(", ")
          }}
        </div>
      </div>
      <div class="row">
        <button @click="edit(g)">Edit</button>
        <button class="danger" @click="remove(g.id)">Delete</button>
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
