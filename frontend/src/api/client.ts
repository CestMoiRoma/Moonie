// Thin typed wrapper around the Moonie REST API.

export interface Health {
  status: string;
  version: string;
  bot_ready: boolean;
  bot_user: string | null;
  guild_count: number;
}

export interface Guild {
  id: string;
  name: string;
  icon_url: string | null;
  member_count: number | null;
}

export interface Role {
  id: string;
  name: string;
  color: number;
  position: number;
  managed: boolean;
}

export interface Channel {
  id: string;
  name: string;
  type: string;
  category_id: string | null;
  position: number;
}

export interface GuildConfig {
  guild_id: string;
  welcome_channel_id: string | null;
  welcome_message: string | null;
  goodbye_channel_id: string | null;
  goodbye_message: string | null;
  autorole_ids: string[];
  log_category_id: string | null;
}

export interface ModAction {
  id: number;
  guild_id: string;
  action: string;
  target_id: string;
  target_tag: string | null;
  moderator_id: string;
  moderator_tag: string | null;
  reason: string | null;
  created_at: string;
}

export interface CommandPermission {
  command: string;
  allowed_role_ids: string[];
  allowed_user_ids: string[];
}

export interface RREntry {
  role_id: string;
  emoji: string | null;
  label: string | null;
}

export interface ReactionRoleMessage {
  id: number;
  guild_id: string;
  channel_id: string;
  message_id: string | null;
  mode: "emoji" | "button";
  title: string | null;
  description: string | null;
  entries: RREntry[];
}

export interface EmbedField {
  name: string;
  value: string;
  inline: boolean;
}

export interface EmbedTemplate {
  id: number;
  guild_id: string;
  name: string;
  title: string | null;
  description: string | null;
  color: number | null;
  fields: EmbedField[];
  footer: string | null;
  image_url: string | null;
  thumbnail_url: string | null;
}

export interface GlobalBan {
  user_id: string;
  reason: string | null;
  added_by: string | null;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore non-JSON bodies */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/health"),

  // Guild introspection
  guilds: () => request<Guild[]>("/guilds"),
  roles: (guildId: string) => request<Role[]>(`/guilds/${guildId}/roles`),
  channels: (guildId: string) => request<Channel[]>(`/guilds/${guildId}/channels`),

  // Settings
  getConfig: (guildId: string) => request<GuildConfig>(`/settings/${guildId}`),
  updateConfig: (guildId: string, body: Record<string, unknown>) =>
    request<GuildConfig>(`/settings/${guildId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  // Welcome preview
  welcomeDefaults: () =>
    request<{ welcome: string; goodbye: string; placeholders: string[] }>(
      "/welcome/defaults",
    ),
  welcomePreview: (template: string) =>
    request<{ rendered: string }>("/welcome/preview", {
      method: "POST",
      body: JSON.stringify({ template }),
    }),

  // Moderation
  modActions: (guildId: string) => request<ModAction[]>(`/moderation/${guildId}/actions`),
  createModAction: (guildId: string, body: Record<string, unknown>) =>
    request<ModAction>(`/moderation/${guildId}/actions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Roles
  roleAdd: (guildId: string, memberId: number, roleName: string) =>
    request<{ message: string }>(`/roles/${guildId}/add`, {
      method: "POST",
      body: JSON.stringify({ member_id: memberId, role_name: roleName }),
    }),

  // Command permissions
  commandList: () => request<string[]>("/permissions/commands"),
  permissions: (guildId: string) => request<CommandPermission[]>(`/permissions/${guildId}`),
  setPermission: (
    guildId: string,
    command: string,
    body: { allowed_role_ids: number[]; allowed_user_ids: number[] },
  ) =>
    request<CommandPermission>(`/permissions/${guildId}/${command}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  // Reaction roles
  reactionRoles: (guildId: string) =>
    request<ReactionRoleMessage[]>(`/reaction-roles/${guildId}`),
  createReactionRole: (guildId: string, body: Record<string, unknown>) =>
    request<ReactionRoleMessage>(`/reaction-roles/${guildId}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteReactionRole: (guildId: string, id: number) =>
    request<void>(`/reaction-roles/${guildId}/${id}`, { method: "DELETE" }),
  publishReactionRole: (guildId: string, id: number) =>
    request<ReactionRoleMessage>(`/reaction-roles/${guildId}/${id}/publish`, {
      method: "POST",
    }),

  // Embeds
  embeds: (guildId: string) => request<EmbedTemplate[]>(`/embeds/${guildId}`),
  createEmbed: (guildId: string, body: Record<string, unknown>) =>
    request<EmbedTemplate>(`/embeds/${guildId}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateEmbed: (guildId: string, id: number, body: Record<string, unknown>) =>
    request<EmbedTemplate>(`/embeds/${guildId}/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteEmbed: (guildId: string, id: number) =>
    request<void>(`/embeds/${guildId}/${id}`, { method: "DELETE" }),
  sendEmbed: (guildId: string, id: number, channelId: string) =>
    request<void>(`/embeds/${guildId}/${id}/send?channel_id=${channelId}`, {
      method: "POST",
    }),

  // Auto-ban
  bans: () => request<GlobalBan[]>("/autoban"),
  addBan: (userId: number, reason: string | null) =>
    request<GlobalBan>("/autoban", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, reason }),
    }),
  removeBan: (userId: string) =>
    request<void>(`/autoban/${userId}`, { method: "DELETE" }),
  importBans: (userIds: number[], reason: string | null) =>
    request<{ added: number; skipped: number }>("/autoban/import", {
      method: "POST",
      body: JSON.stringify({ user_ids: userIds, reason }),
    }),
};
