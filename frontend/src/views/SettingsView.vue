<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api, type Channel, type Role } from "../api/client";

const props = defineProps<{ guildId: string }>();

const channels = ref<Channel[]>([]);
const categories = ref<Channel[]>([]);
const roles = ref<Role[]>([]);

const welcomeChannel = ref<string>("");
const welcomeMessage = ref<string>("");
const goodbyeChannel = ref<string>("");
const goodbyeMessage = ref<string>("");
const autoroleIds = ref<string[]>([]);
const logCategory = ref<string>("");

const preview = ref<string>("");
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);
const saving = ref(false);

async function load() {
  toast.value = null;
  const [chs, rls, cfg] = await Promise.all([
    api.channels(props.guildId),
    api.roles(props.guildId),
    api.getConfig(props.guildId),
  ]);
  channels.value = chs.filter((c) => c.type === "text");
  categories.value = chs.filter((c) => c.type === "category");
  roles.value = rls;

  welcomeChannel.value = cfg.welcome_channel_id ?? "";
  welcomeMessage.value = cfg.welcome_message ?? "";
  goodbyeChannel.value = cfg.goodbye_channel_id ?? "";
  goodbyeMessage.value = cfg.goodbye_message ?? "";
  autoroleIds.value = cfg.autorole_ids ?? [];
  logCategory.value = cfg.log_category_id ?? "";
  await refreshPreview();
}

async function refreshPreview() {
  const tpl = welcomeMessage.value.trim();
  preview.value = tpl ? (await api.welcomePreview(tpl)).rendered : "";
}

async function save() {
  saving.value = true;
  toast.value = null;
  try {
    await api.updateConfig(props.guildId, {
      welcome_channel_id: welcomeChannel.value ? Number(welcomeChannel.value) : null,
      welcome_message: welcomeMessage.value || null,
      goodbye_channel_id: goodbyeChannel.value ? Number(goodbyeChannel.value) : null,
      goodbye_message: goodbyeMessage.value || null,
      autorole_ids: autoroleIds.value.map(Number),
      log_category_id: logCategory.value ? Number(logCategory.value) : null,
    });
    toast.value = { kind: "ok", text: "Settings saved." };
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  } finally {
    saving.value = false;
  }
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Welcome &amp; Roles</h2>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>Welcome message</h3>
    <div class="field">
      <label>Channel</label>
      <select v-model="welcomeChannel">
        <option value="">— Disabled —</option>
        <option v-for="c in channels" :key="c.id" :value="c.id">#{{ c.name }}</option>
      </select>
    </div>
    <div class="field">
      <label>Message (placeholders: {user_mention}, {user_name}, {server}, {member_count})</label>
      <textarea v-model="welcomeMessage" rows="2" @input="refreshPreview"></textarea>
    </div>
    <div v-if="preview" class="field">
      <label>Preview</label>
      <div class="card preview">{{ preview }}</div>
    </div>
  </div>

  <div class="card">
    <h3>Goodbye message</h3>
    <div class="field">
      <label>Channel</label>
      <select v-model="goodbyeChannel">
        <option value="">— Disabled —</option>
        <option v-for="c in channels" :key="c.id" :value="c.id">#{{ c.name }}</option>
      </select>
    </div>
    <div class="field">
      <label>Message</label>
      <textarea v-model="goodbyeMessage" rows="2"></textarea>
    </div>
  </div>

  <div class="card">
    <h3>Autoroles</h3>
    <p class="muted">Roles automatically granted when a member joins (Ctrl/Cmd-click to multi-select).</p>
    <select v-model="autoroleIds" multiple size="6">
      <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
    </select>
  </div>

  <div class="card">
    <h3>Logging category</h3>
    <p class="muted">Category under which per-user log channels are created (used by later features).</p>
    <select v-model="logCategory">
      <option value="">— None —</option>
      <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
    </select>
  </div>

  <button class="primary" :disabled="saving" @click="save">
    {{ saving ? "Saving…" : "Save settings" }}
  </button>
</template>

<style scoped>
.preview {
  background: var(--bg-elev2);
  margin: 0;
}
</style>
