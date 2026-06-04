import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", name: "dashboard", component: () => import("./views/DashboardView.vue") },
  { path: "/settings", name: "settings", component: () => import("./views/SettingsView.vue") },
  { path: "/moderation", name: "moderation", component: () => import("./views/ModerationView.vue") },
  { path: "/roles", name: "roles", component: () => import("./views/RolesView.vue") },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
