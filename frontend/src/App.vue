<script setup lang="ts">
import { onMounted, ref } from "vue";
import { guildState, loadGuilds, selectGuild } from "./store/guild";
import { api, type Health } from "./api/client";

const health = ref<Health | null>(null);
const error = ref<string | null>(null);

const nav = [
  { to: "/", label: "Dashboard", icon: "🏠" },
  { to: "/settings", label: "Welcome & Roles", icon: "⚙️" },
  { to: "/moderation", label: "Moderation", icon: "🛡️" },
  { to: "/roles", label: "Role Add", icon: "🎨" },
  { to: "/permissions", label: "Permissions", icon: "🔑" },
  { to: "/reaction-roles", label: "Reaction Roles", icon: "✨" },
  { to: "/embeds", label: "Embeds", icon: "📋" },
  { to: "/autoban", label: "Auto-Ban", icon: "🚫" },
  { to: "/groups", label: "Groups", icon: "🗂️" },
  { to: "/bulk-permissions", label: "Bulk Perms", icon: "🔧" },
  { to: "/forms", label: "Forms", icon: "📝" },
  { to: "/user-logging", label: "User Logging", icon: "🔍" },
  { to: "/custom-commands", label: "Custom Commands", icon: "💬" },
  { to: "/automod", label: "Automod", icon: "🤖" },
];

onMounted(async () => {
  try {
    health.value = await api.health();
    if (health.value.bot_ready) await loadGuilds();
  } catch (e) {
    error.value = (e as Error).message;
  }
});

function onSelect(event: Event) {
  selectGuild((event.target as HTMLSelectElement).value);
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">🌙 <span>Moonie</span></div>
      <nav>
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-link">
          <span class="icon">{{ item.icon }}</span>{{ item.label }}
        </RouterLink>
      </nav>
      <div class="status">
        <span
          class="dot"
          :class="{ on: health?.bot_ready, off: !health?.bot_ready }"
        ></span>
        <span class="muted">
          {{ health?.bot_ready ? health?.bot_user : "Bot offline" }}
        </span>
      </div>
    </aside>

    <main class="content">
      <header class="topbar">
        <label class="muted">Guild</label>
        <select
          v-if="guildState.guilds.length"
          :value="guildState.selectedId ?? ''"
          @change="onSelect"
        >
          <option v-for="g in guildState.guilds" :key="g.id" :value="g.id">
            {{ g.name }}
          </option>
        </select>
        <span v-else class="muted">
          {{ health?.bot_ready ? "No guilds — invite the bot to a server." : "Waiting for bot…" }}
        </span>
      </header>

      <div v-if="error" class="toast err">{{ error }}</div>

      <RouterView v-if="guildState.selectedId" :guild-id="guildState.selectedId" />
      <div v-else class="card muted">
        Select a guild to begin. If the list is empty, make sure the bot has a token and
        has been invited to your server.
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
}
.sidebar {
  background: var(--bg-elev);
  border-right: 1px solid var(--border);
  padding: 18px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.brand {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 18px;
  padding: 0 6px;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  color: var(--text-dim);
}
.nav-link:hover {
  background: var(--bg-elev2);
  color: var(--text);
}
.nav-link.router-link-active {
  background: var(--accent);
  color: #fff;
}
.status {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  font-size: 12px;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.dot.on {
  background: var(--ok);
}
.dot.off {
  background: var(--danger);
}
.content {
  padding: 22px 28px;
  max-width: 880px;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
.topbar select {
  width: auto;
  min-width: 200px;
}
</style>
