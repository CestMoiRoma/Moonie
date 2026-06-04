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
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
