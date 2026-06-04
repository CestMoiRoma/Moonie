import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", name: "dashboard", component: () => import("./views/DashboardView.vue") },
  { path: "/settings", name: "settings", component: () => import("./views/SettingsView.vue") },
  { path: "/moderation", name: "moderation", component: () => import("./views/ModerationView.vue") },
  { path: "/roles", name: "roles", component: () => import("./views/RolesView.vue") },
  { path: "/permissions", name: "permissions", component: () => import("./views/PermissionsView.vue") },
  { path: "/reaction-roles", name: "reaction-roles", component: () => import("./views/ReactionRolesView.vue") },
  { path: "/embeds", name: "embeds", component: () => import("./views/EmbedsView.vue") },
  { path: "/autoban", name: "autoban", component: () => import("./views/AutoBanView.vue") },
  { path: "/groups", name: "groups", component: () => import("./views/GroupsView.vue") },
  { path: "/bulk-permissions", name: "bulk-permissions", component: () => import("./views/BulkPermissionsView.vue") },
  { path: "/forms", name: "forms", component: () => import("./views/FormsView.vue") },
  { path: "/user-logging", name: "user-logging", component: () => import("./views/UserLoggingView.vue") },
  { path: "/custom-commands", name: "custom-commands", component: () => import("./views/CustomCommandsView.vue") },
  { path: "/automod", name: "automod", component: () => import("./views/AutomodView.vue") },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
