<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { api, type BulkResult, type Channel, type Group, type Role } from "../api/client";

const props = defineProps<{ guildId: string }>();

const roles = ref<Role[]>([]);
const channels = ref<Channel[]>([]);
const categories = ref<Channel[]>([]);
const groups = ref<Group[]>([]);
const permNames = ref<string[]>([]);
const result = ref<BulkResult | null>(null);
const toast = ref<{ kind: "ok" | "err"; text: string } | null>(null);

const sel = reactive({
  targetType: "role" as "role" | "member",
  roleId: "",
  memberId: "",
  source: "channels" as "channels" | "category" | "group",
  channelIds: [] as string[],
  categoryId: "",
  groupId: "",
});

// perm name -> "inherit" | "allow" | "deny"
const perms = reactive<Record<string, string>>({});

const resolvedChannelIds = computed<string[]>(() => {
  if (sel.source === "channels") return sel.channelIds;
  if (sel.source === "category") {
    return channels.value.filter((c) => c.category_id === sel.categoryId).map((c) => c.id);
  }
  const g = groups.value.find((g) => String(g.id) === sel.groupId);
  return g ? g.items.filter((i) => i.kind === "channel").map((i) => i.discord_id) : [];
});

async function load() {
  const [rls, chs, gs, pns] = await Promise.all([
    api.roles(props.guildId),
    api.channels(props.guildId),
    api.groups(props.guildId),
    api.supportedPermissions(),
  ]);
  roles.value = rls;
  channels.value = chs.filter((c) => c.type === "text" || c.type === "voice");
  categories.value = chs.filter((c) => c.type === "category");
  groups.value = gs;
  permNames.value = pns;
  for (const p of pns) if (!(p in perms)) perms[p] = "inherit";
}

async function apply() {
  toast.value = null;
  result.value = null;
  const targetId = sel.targetType === "role" ? sel.roleId : sel.memberId;
  if (!targetId) {
    toast.value = { kind: "err", text: "Choose a target role or member." };
    return;
  }
  const channelIds = resolvedChannelIds.value;
  if (!channelIds.length) {
    toast.value = { kind: "err", text: "No channels selected." };
    return;
  }
  const overwrites: Record<string, boolean | null> = {};
  for (const p of permNames.value) {
    overwrites[p] = perms[p] === "allow" ? true : perms[p] === "deny" ? false : null;
  }
  try {
    result.value = await api.applyBulkPermissions(props.guildId, {
      target_type: sel.targetType,
      target_id: Number(targetId),
      channel_ids: channelIds.map(Number),
      overwrites,
    });
    toast.value = {
      kind: "ok",
      text: `Applied to ${result.value.applied} channel(s), ${result.value.failed} failed.`,
    };
  } catch (e) {
    toast.value = { kind: "err", text: (e as Error).message };
  }
}

onMounted(load);
watch(() => props.guildId, load);
</script>

<template>
  <h2>Bulk Channel Permissions</h2>
  <p class="muted">
    Apply one permission overwrite to many channels at once, for a single role or member.
    Inherit = leave at the server/category default.
  </p>
  <div v-if="toast" class="toast" :class="toast.kind">{{ toast.text }}</div>

  <div class="card">
    <h3>Target</h3>
    <div class="row">
      <div class="field" style="flex: 0 0 140px">
        <label>Type</label>
        <select v-model="sel.targetType">
          <option value="role">Role</option>
          <option value="member">Member</option>
        </select>
      </div>
      <div v-if="sel.targetType === 'role'" class="field" style="flex: 1 1 200px">
        <label>Role</label>
        <select v-model="sel.roleId">
          <option value="">— Select —</option>
          <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
      <div v-else class="field" style="flex: 1 1 200px">
        <label>Member user id</label>
        <input v-model="sel.memberId" placeholder="123456789012345678" />
      </div>
    </div>
  </div>

  <div class="card">
    <h3>Channels</h3>
    <div class="field" style="max-width: 240px">
      <label>Source</label>
      <select v-model="sel.source">
        <option value="channels">Pick channels</option>
        <option value="category">All in a category</option>
        <option value="group">A group's channels</option>
      </select>
    </div>
    <div v-if="sel.source === 'channels'" class="field">
      <select v-model="sel.channelIds" multiple size="6">
        <option v-for="c in channels" :key="c.id" :value="c.id">#{{ c.name }}</option>
      </select>
    </div>
    <div v-else-if="sel.source === 'category'" class="field" style="max-width: 280px">
      <select v-model="sel.categoryId">
        <option value="">— Select category —</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>
    <div v-else class="field" style="max-width: 280px">
      <select v-model="sel.groupId">
        <option value="">— Select group —</option>
        <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
      </select>
    </div>
    <p class="muted">{{ resolvedChannelIds.length }} channel(s) targeted.</p>
  </div>

  <div class="card">
    <h3>Permissions</h3>
    <div class="perms">
      <div v-for="p in permNames" :key="p" class="perm">
        <span>{{ p.replace(/_/g, " ") }}</span>
        <select v-model="perms[p]">
          <option value="inherit">Inherit</option>
          <option value="allow">Allow</option>
          <option value="deny">Deny</option>
        </select>
      </div>
    </div>
    <button class="primary" @click="apply" style="margin-top: 14px">Apply overwrite</button>
  </div>

  <div v-if="result" class="card">
    <h3>Result</h3>
    <table>
      <thead>
        <tr><th>Channel</th><th>Status</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in result.results" :key="r.channel_id">
          <td>{{ r.channel_name }}</td>
          <td>
            <span v-if="r.ok" class="pill" style="border-color: var(--ok)">ok</span>
            <span v-else class="pill" style="border-color: var(--danger)">{{ r.error }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.perms {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.perm {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.perm span {
  text-transform: capitalize;
  color: var(--text-dim);
  font-size: 13px;
}
.perm select {
  width: auto;
  min-width: 90px;
}
</style>
