<script setup lang="ts">
import { ref } from "vue";
import { api } from "../api/client";

const props = defineProps<{ guildId: string }>();

const memberId = ref("");
const roleName = ref("");
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);
const busy = ref(false);

async function submit() {
  if (!memberId.value || !roleName.value) {
    toast.value = { kind: "err", text: "Member id and role name are required." };
    return;
  }
  busy.value = true;
  toast.value = null;
  try {
    const res = await api.roleAdd(props.guildId, Number(memberId.value), roleName.value);
    toast.value = { kind: "ok", text: res.message };
    memberId.value = "";
    roleName.value = "";
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <h2>Role Add</h2>
  <p class="muted">
    Give a member an aesthetic (zero-permission) role. The role is created automatically
    if it doesn't already exist.
  </p>

  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <div class="field">
      <label>Member user id</label>
      <input v-model="memberId" placeholder="123456789012345678" />
    </div>
    <div class="field">
      <label>Role name</label>
      <input v-model="roleName" placeholder="e.g. Night Owl" />
    </div>
    <button class="primary" :disabled="busy" @click="submit">
      {{ busy ? "Working…" : "Add role" }}
    </button>
  </div>
</template>
