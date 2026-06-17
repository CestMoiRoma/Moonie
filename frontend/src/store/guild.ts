// Shared reactive state for the currently selected guild.

import { reactive, readonly } from "vue";
import { api, type Guild } from "../api/client";

interface GuildState {
  guilds: Guild[];
  selectedId: string | null;
  loaded: boolean;
}

const state = reactive<GuildState>({
  guilds: [],
  selectedId: localStorage.getItem("moonie.guildId"),
  loaded: false,
});

export async function loadGuilds(): Promise<void> {
  state.guilds = await api.guilds();
  if (!state.selectedId && state.guilds.length > 0) {
    selectGuild(state.guilds[0].id);
  }
  state.loaded = true;
}

export function selectGuild(id: string): void {
  state.selectedId = id;
  localStorage.setItem("moonie.guildId", id);
}

export const guildState = readonly(state);
