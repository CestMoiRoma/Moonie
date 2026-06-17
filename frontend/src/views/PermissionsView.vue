<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { api, type Role } from "../api/client";

const props = defineProps<{ guildId: string }>();

const commands = ref<string[]>([]);
const roles = ref<Role[]>([]);
const roleSel = reactive<Record<string, string[]>>({});
const userIds = reactive<Record<string, string>>({});
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

async function load() {
  toast.value = null;
  try {
    const [cmds, rls, perms] = await Promise.all([
      api.commandList(),
      api.roles(props.guildId),
      api.permissions(props.guildId),
    ]);
    commands.value = cmds;
    roles.value = rls;
    const byCmd = Object.fromEntries(perms.map((p) => [p.command, p]));
    for (const c of cmds) {
      roleSel[c] = byCmd[c]?.allowed_role_ids ?? [];
      userIds[c] = (byCmd[c]?.allowed_user_ids ?? []).join(", ");
    }
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

async function save(command: string) {
  toast.value = null;
  try {
    const users = userIds[command]
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number);
    await api.setPermission(props.guildId, command, {
      allowed_role_ids: roleSel[command].map(Number),
      allowed_user_ids: users,
    });
    toast.value = { kind: "ok", text: `Saved permissions for /${command}.` };
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Command Permissions</h2>
  <p class="muted">
    Restrict who can run each slash command. Leave a command empty to keep it open to
    everyone. Guild owner and administrators always bypass these rules.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div v-for="c in commands" :key="c" class="card">
    <h3>/{{ c }}</h3>
    <div class="row">
      <div class="field" style="flex: 1 1 220px">
        <label>Allowed roles (Ctrl/Cmd-click to multi-select)</label>
        <select v-model="roleSel[c]" multiple size="4">
          <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
      <div class="field" style="flex: 1 1 220px">
        <label>Allowed user ids (comma-separated)</label>
        <input v-model="userIds[c]" placeholder="123, 456" />
      </div>
    </div>
    <button class="primary" @click="save(c)">Save</button>
  </div>

  <p v-if="!commands.length" class="muted">
    No commands found — the bot needs to be online to list its commands.
  </p>
</template>
