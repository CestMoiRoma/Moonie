<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type Health } from "../api/client";
import { guildState } from "../store/guild";

defineProps<{ guildId: string }>();

const health = ref<Health | null>(null);
onMounted(async () => {
  health.value = await api.health();
});
</script>

<template>
  <h2>Dashboard</h2>
  <div class="card">
    <div class="grid">
      <div>
        <div class="muted">Bot</div>
        <div class="big">{{ health?.bot_ready ? "Online" : "Offline" }}</div>
        <div class="muted">{{ health?.bot_user ?? "—" }}</div>
      </div>
      <div>
        <div class="muted">Guilds</div>
        <div class="big">{{ health?.guild_count ?? 0 }}</div>
      </div>
      <div>
        <div class="muted">Version</div>
        <div class="big">v{{ health?.version ?? "?" }}</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h3>Selected guild</h3>
    <p class="muted">
      Acting on <span class="pill">{{ guildState.selectedId }}</span
      >. Use the pages on the left to configure welcome messages, autoroles, run
      moderation actions, or add aesthetic roles.
    </p>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}
.big {
  font-size: 26px;
  font-weight: 700;
  margin: 4px 0;
}
</style>
