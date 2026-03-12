const API_BASE_STORAGE_KEY = "assistant_api_base_url";
const BROKER_WORKSPACE_STORAGE_KEY = "assistant_memory_broker_workspace_id";
const CACHE_DB_NAME = "assistant-web-shell";
const CACHE_DB_VERSION = 1;
const CACHE_STORE_NAME = "snapshots";
const DEFAULT_ROUTE = "/chat/conv_shell";
const DEFAULT_BROKER_WORKSPACE_ID = "workspace_shell";
const DEFAULT_REMINDER_RETRY_ATTEMPTS = 2;
const DEFAULT_REMINDER_RETRY_DELAY_SECONDS = 300;

const state = {
  apiBase: localStorage.getItem(API_BASE_STORAGE_KEY) || "http://127.0.0.1:8000",
  session: null,
  telegramLink: null,
  reminders: [],
  memoryItems: [],
  memoryBrokerWorkspaceId: localStorage.getItem(BROKER_WORKSPACE_STORAGE_KEY) || DEFAULT_BROKER_WORKSPACE_ID,
  memoryBrokerState: null,
  memoryBrokerProbe: null,
  checkpoint: null,
  checkpointDraft: null,
  checkpointDirty: false,
  checkpointConflict: null,
  runtimeJobs: [],
  trust: null,
  selectedMemoryIds: new Set(),
  lastMemoryExport: null,
  notice: { text: "", tone: "info" },
};

const elements = {
  apiBaseInput: document.querySelector("#apiBaseInput"),
  connectButton: document.querySelector("#connectButton"),
  refreshButton: document.querySelector("#refreshButton"),
  runtimeMeta: document.querySelector("#runtimeMeta"),
  notice: document.querySelector("#notice"),
  sessionCard: document.querySelector("#sessionCard"),
  telegramCard: document.querySelector("#telegramCard"),
  reminderForm: document.querySelector("#reminderForm"),
  reminderAtInput: document.querySelector("#reminderAtInput"),
  reminderMessageInput: document.querySelector("#reminderMessageInput"),
  reminderFollowUpActionInput: document.querySelector("#reminderFollowUpActionInput"),
  reminderMaxAttemptsInput: document.querySelector("#reminderMaxAttemptsInput"),
  reminderRetryDelayInput: document.querySelector("#reminderRetryDelayInput"),
  reminderFollowUpMeta: document.querySelector("#reminderFollowUpMeta"),
  saveReminderButton: document.querySelector("#saveReminderButton"),
  remindersMeta: document.querySelector("#remindersMeta"),
  remindersCard: document.querySelector("#remindersCard"),
  checkpointForm: document.querySelector("#checkpointForm"),
  checkpointConflict: document.querySelector("#checkpointConflict"),
  conversationIdInput: document.querySelector("#conversationIdInput"),
  lastMessageIdInput: document.querySelector("#lastMessageIdInput"),
  routeInput: document.querySelector("#routeInput"),
  draftInput: document.querySelector("#draftInput"),
  checkpointMeta: document.querySelector("#checkpointMeta"),
  checkpointContinuity: document.querySelector("#checkpointContinuity"),
  memoryForm: document.querySelector("#memoryForm"),
  memoryKindInput: document.querySelector("#memoryKindInput"),
  memoryImportanceInput: document.querySelector("#memoryImportanceInput"),
  memoryContentInput: document.querySelector("#memoryContentInput"),
  memorySourceNoteInput: document.querySelector("#memorySourceNoteInput"),
  exportMemoryButton: document.querySelector("#exportMemoryButton"),
  memoryExportMeta: document.querySelector("#memoryExportMeta"),
  memoryList: document.querySelector("#memoryList"),
  memoryBrokerForm: document.querySelector("#memoryBrokerForm"),
  brokerWorkspaceIdInput: document.querySelector("#brokerWorkspaceIdInput"),
  brokerProjectIdsInput: document.querySelector("#brokerProjectIdsInput"),
  brokerEnabledInput: document.querySelector("#brokerEnabledInput"),
  saveBrokerButton: document.querySelector("#saveBrokerButton"),
  brokerMeta: document.querySelector("#brokerMeta"),
  brokerQueryInput: document.querySelector("#brokerQueryInput"),
  brokerQueryProjectIdInput: document.querySelector("#brokerQueryProjectIdInput"),
  probeBrokerButton: document.querySelector("#probeBrokerButton"),
  brokerProbeMeta: document.querySelector("#brokerProbeMeta"),
  brokerCard: document.querySelector("#brokerCard"),
  trustCard: document.querySelector("#trustCard"),
  jobsCard: document.querySelector("#jobsCard"),
};

function normalizeApiBase(rawValue) {
  return rawValue.trim().replace(/\/+$/, "");
}

function setNotice(text, tone = "info") {
  state.notice = { text, tone };
  elements.notice.textContent = text;
  elements.notice.dataset.tone = tone;
}

function setRuntimeMeta(text) {
  elements.runtimeMeta.textContent = text;
}

function formatDate(value) {
  if (!value) {
    return "Not set";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatDurationSeconds(value) {
  const seconds = Number.parseInt(String(value ?? 0), 10);
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "Immediate retry";
  }
  if (seconds % 3600 === 0) {
    const hours = seconds / 3600;
    return `${hours} hour${hours === 1 ? "" : "s"}`;
  }
  if (seconds % 60 === 0) {
    const minutes = seconds / 60;
    return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  }
  return `${seconds} second${seconds === 1 ? "" : "s"}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function humanizeLabel(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function cloneJson(value) {
  return value ? JSON.parse(JSON.stringify(value)) : null;
}

function appReturnUrl() {
  const url = new URL(window.location.href);
  url.search = "";
  url.hash = "";
  return url.toString();
}

function hasActiveSession() {
  return Boolean(state.session && state.session.auth_state === "active");
}

function inferPlatform() {
  const userAgent = navigator.userAgent.toLowerCase();
  if (navigator.standalone || window.matchMedia("(display-mode: standalone)").matches) {
    return "pwa";
  }
  if (userAgent.includes("iphone") || userAgent.includes("ipad")) {
    return "ios_webview";
  }
  if (userAgent.includes("android") && userAgent.includes("wv")) {
    return "android_webview";
  }
  return "web";
}

function inferDeviceLabel() {
  const platform = navigator.platform || "Unknown platform";
  const language = navigator.language || "unknown";
  return `${platform} - ${language}`;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${state.apiBase}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    ...options,
  });
  if (response.status === 204) {
    return null;
  }
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail =
      payload && typeof payload.detail === "string"
        ? payload.detail
        : payload && typeof payload.message === "string"
          ? payload.message
          : response.statusText;
    const error = new Error(detail);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

async function openCacheDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(CACHE_DB_NAME, CACHE_DB_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(CACHE_STORE_NAME)) {
        database.createObjectStore(CACHE_STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function cacheWrite(key, value) {
  try {
    const database = await openCacheDb();
    await new Promise((resolve, reject) => {
      const transaction = database.transaction(CACHE_STORE_NAME, "readwrite");
      transaction.objectStore(CACHE_STORE_NAME).put(value, key);
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  } catch {
    return;
  }
}

async function cacheRead(key) {
  try {
    const database = await openCacheDb();
    return await new Promise((resolve, reject) => {
      const transaction = database.transaction(CACHE_STORE_NAME, "readonly");
      const request = transaction.objectStore(CACHE_STORE_NAME).get(key);
      request.onsuccess = () => resolve(request.result ?? null);
      request.onerror = () => reject(request.error);
    });
  } catch {
    return null;
  }
}

function normalizeCheckpointSnapshot(snapshot) {
  if (!snapshot) {
    return null;
  }
  if (snapshot.checkpoint) {
    return {
      checkpoint: snapshot.checkpoint,
      dirty: Boolean(snapshot.dirty),
      cached_at: snapshot.cached_at || null,
    };
  }
  return {
    checkpoint: snapshot,
    dirty: false,
    cached_at: null,
  };
}

function checkpointSignature(checkpoint) {
  if (!checkpoint) {
    return "";
  }
  return JSON.stringify({
    conversation_id: checkpoint.conversation_id || "",
    last_message_id: checkpoint.last_message_id || "",
    draft_text: checkpoint.draft_text || "",
    selected_memory_ids: [...(checkpoint.selected_memory_ids || [])].sort(),
    route: checkpoint.route || "",
    surface: checkpoint.surface || "web",
    handoff_kind: checkpoint.handoff_kind || "none",
    resume_token_ref: checkpoint.resume_token_ref || null,
    last_surface_at: checkpoint.last_surface_at || null,
  });
}

function checkpointsDiffer(left, right) {
  return checkpointSignature(left) !== checkpointSignature(right);
}

function nextCheckpointVersion() {
  if (state.checkpoint) {
    return state.checkpoint.version + 1;
  }
  if (state.checkpointDraft) {
    return Math.max(state.checkpointDraft.version, 1);
  }
  return 1;
}

function buildCheckpointDraftFromForm(version = nextCheckpointVersion()) {
  if (!hasActiveSession()) {
    return null;
  }
  const priorCheckpoint = state.checkpointDraft || state.checkpoint;
  return {
    user_id: state.session.user_id,
    device_session_id: state.session.device_session_id,
    conversation_id: elements.conversationIdInput.value.trim() || "conv_shell",
    last_message_id: elements.lastMessageIdInput.value.trim() || null,
    draft_text: elements.draftInput.value,
    selected_memory_ids: [...state.selectedMemoryIds],
    route: elements.routeInput.value.trim() || DEFAULT_ROUTE,
    surface: inferPlatform(),
    handoff_kind: priorCheckpoint?.handoff_kind || "none",
    resume_token_ref: priorCheckpoint?.resume_token_ref || null,
    last_surface_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    version,
  };
}

async function persistCheckpointDraft() {
  if (!state.checkpointDraft) {
    await cacheWrite("checkpoint", null);
    return;
  }
  await cacheWrite("checkpoint", {
    checkpoint: state.checkpointDraft,
    dirty: state.checkpointDirty,
    cached_at: new Date().toISOString(),
  });
}

function applyCheckpointDraftToForm() {
  const checkpoint = state.checkpointDraft || state.checkpoint;
  if (!hasActiveSession()) {
    elements.conversationIdInput.value = "";
    elements.lastMessageIdInput.value = "";
    elements.routeInput.value = DEFAULT_ROUTE;
    elements.draftInput.value = "";
    return;
  }
  if (!checkpoint) {
    elements.conversationIdInput.value = "";
    elements.lastMessageIdInput.value = "";
    if (!elements.routeInput.value) {
      elements.routeInput.value = DEFAULT_ROUTE;
    }
    if (!elements.draftInput.value) {
      elements.draftInput.value = "";
    }
    return;
  }
  elements.conversationIdInput.value = checkpoint.conversation_id || "";
  elements.lastMessageIdInput.value = checkpoint.last_message_id || "";
  elements.routeInput.value = checkpoint.route || DEFAULT_ROUTE;
  elements.draftInput.value = checkpoint.draft_text || "";
}

function updateCheckpointMeta() {
  if (!hasActiveSession()) {
    elements.checkpointMeta.textContent = "Complete sign-in before syncing a checkpoint.";
    return;
  }
  if (state.checkpointConflict) {
    elements.checkpointMeta.textContent = `Conflict detected | server v${state.checkpointConflict.server.version} | local draft ${formatDate(state.checkpointConflict.local.updated_at)}`;
    return;
  }
  if (state.checkpointDirty && state.checkpointDraft) {
    const basis = state.checkpoint ? `server v${state.checkpoint.version}` : "no server checkpoint yet";
    elements.checkpointMeta.textContent = `Local draft pending sync | based on ${basis}`;
    return;
  }
  if (state.checkpoint) {
    elements.checkpointMeta.textContent = `Version ${state.checkpoint.version} | synced ${formatDate(state.checkpoint.updated_at)}`;
    return;
  }
  if (state.checkpointDraft) {
    elements.checkpointMeta.textContent = "Draft cached locally and ready to sync.";
    return;
  }
  elements.checkpointMeta.textContent = "No synced checkpoint yet.";
}

function renderCheckpointConflict() {
  if (!hasActiveSession() || !state.checkpointConflict) {
    elements.checkpointConflict.hidden = true;
    elements.checkpointConflict.innerHTML = "";
    return;
  }

  const { server, local } = state.checkpointConflict;
  elements.checkpointConflict.hidden = false;
  elements.checkpointConflict.innerHTML = `
    <div class="checkpoint-summary checkpoint-conflict-card">
      <span class="pill" data-status="warn">Conflict detected</span>
      <h3>Choose which draft wins</h3>
      <p>Another copy of this checkpoint moved ahead on the server. Keep the cloud copy or force your local draft back up.</p>
      <dl>
        ${kvRow("Server draft", `${server.conversation_id} | v${server.version}`)}
        ${kvRow("Server synced", formatDate(server.updated_at))}
        ${kvRow("Local draft", `${local.conversation_id} | v${local.version}`)}
        ${kvRow("Local edited", formatDate(local.updated_at))}
      </dl>
      <div class="cluster">
        <button class="button" type="button" data-conflict-action="server">Use Server Copy</button>
        <button class="button button-strong" type="button" data-conflict-action="force">Keep Local Draft</button>
      </div>
    </div>
  `;
}

async function hydrateFromCache() {
  const [
    session,
    telegramLink,
    reminders,
    memoryItems,
    memoryBrokerState,
    memoryBrokerProbe,
    checkpointSnapshot,
    runtimeJobs,
    trust,
    lastMemoryExport,
  ] = await Promise.all([
    cacheRead("session"),
    cacheRead("telegram_link"),
    cacheRead("reminders"),
    cacheRead("memory"),
    cacheRead("memory_broker_state"),
    cacheRead("memory_broker_probe"),
    cacheRead("checkpoint"),
    cacheRead("runtime_jobs"),
    cacheRead("trust"),
    cacheRead("memory_export"),
  ]);
  if (session) {
    state.session = session;
  }
  if (telegramLink) {
    state.telegramLink = telegramLink;
  }
  if (Array.isArray(reminders)) {
    state.reminders = reminders;
  }
  if (Array.isArray(memoryItems)) {
    state.memoryItems = memoryItems;
  }
  if (memoryBrokerState?.workspace_id === state.memoryBrokerWorkspaceId) {
    state.memoryBrokerState = memoryBrokerState;
  }
  if (memoryBrokerProbe?.workspace_id === state.memoryBrokerWorkspaceId) {
    state.memoryBrokerProbe = memoryBrokerProbe;
  }
  const normalizedCheckpoint = normalizeCheckpointSnapshot(checkpointSnapshot);
  if (normalizedCheckpoint && normalizedCheckpoint.checkpoint) {
    state.checkpointDraft = normalizedCheckpoint.checkpoint;
    state.checkpointDirty = normalizedCheckpoint.dirty;
    state.selectedMemoryIds = new Set(normalizedCheckpoint.checkpoint.selected_memory_ids || []);
    if (!normalizedCheckpoint.dirty) {
      state.checkpoint = normalizedCheckpoint.checkpoint;
    }
  }
  if (trust) {
    state.trust = trust;
  }
  if (Array.isArray(runtimeJobs)) {
    state.runtimeJobs = runtimeJobs;
  }
  if (lastMemoryExport) {
    state.lastMemoryExport = lastMemoryExport;
  }
  renderAll();
}

function kvRow(label, value) {
  return `<div class="kv-row"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`;
}

function toLocalDateTimeValue(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const year = String(date.getFullYear());
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function nextReminderDateTimeValue() {
  const nextHour = new Date();
  nextHour.setSeconds(0, 0);
  nextHour.setMinutes(0);
  nextHour.setHours(nextHour.getHours() + 1);
  return toLocalDateTimeValue(nextHour);
}

function ensureReminderDefaults() {
  if (!elements.reminderAtInput.value) {
    elements.reminderAtInput.value = nextReminderDateTimeValue();
  }
  if (!elements.reminderMaxAttemptsInput.value) {
    elements.reminderMaxAttemptsInput.value = String(DEFAULT_REMINDER_RETRY_ATTEMPTS);
  }
  if (!elements.reminderRetryDelayInput.value) {
    elements.reminderRetryDelayInput.value = String(DEFAULT_REMINDER_RETRY_DELAY_SECONDS);
  }
}

function reminderMessage(reminder) {
  return typeof reminder?.payload?.message === "string" && reminder.payload.message.trim()
    ? reminder.payload.message.trim()
    : "Reminder message missing";
}

function reminderEventAt(reminder) {
  if (!reminder) {
    return null;
  }
  if (reminder.status === "delivered") {
    return reminder.delivered_at || reminder.updated_at;
  }
  if (reminder.status === "canceled") {
    return reminder.canceled_at || reminder.updated_at;
  }
  return reminder.updated_at || reminder.created_at;
}

function reminderEventLabel(reminder) {
  if (!reminder) {
    return "Updated";
  }
  if (reminder.status === "delivered") {
    return "Delivered";
  }
  if (reminder.status === "canceled") {
    return "Canceled";
  }
  if (reminder.status === "failed") {
    return "Failed";
  }
  return "Updated";
}

function reminderFollowUpPolicy(reminder) {
  const rawPolicy = reminder?.follow_up_policy || {};
  const onFailure = rawPolicy.on_failure === "retry" ? "retry" : "none";
  const maxAttempts =
    Number.isInteger(rawPolicy.max_attempts) && rawPolicy.max_attempts > 0
      ? rawPolicy.max_attempts
      : onFailure === "retry"
        ? DEFAULT_REMINDER_RETRY_ATTEMPTS
        : 1;
  const retryDelaySeconds =
    Number.isInteger(rawPolicy.retry_delay_seconds) && rawPolicy.retry_delay_seconds >= 0
      ? rawPolicy.retry_delay_seconds
      : 0;
  return {
    on_failure: onFailure,
    max_attempts: maxAttempts,
    retry_delay_seconds: retryDelaySeconds,
  };
}

function reminderFollowUpState(reminder) {
  const rawState = reminder?.follow_up_state || {};
  return {
    status: typeof rawState.status === "string" ? rawState.status : "none",
    attempt_count:
      Number.isInteger(rawState.attempt_count) && rawState.attempt_count >= 0 ? rawState.attempt_count : 0,
    next_attempt_at: typeof rawState.next_attempt_at === "string" ? rawState.next_attempt_at : null,
    last_transition_reason:
      typeof rawState.last_transition_reason === "string" ? rawState.last_transition_reason : null,
  };
}

function reminderRetryReady(reminder) {
  const policy = reminderFollowUpPolicy(reminder);
  const followUpState = reminderFollowUpState(reminder);
  return policy.on_failure === "retry" && reminder.status === "scheduled" && followUpState.status === "none";
}

function reminderAttemptBudget(reminder) {
  const policy = reminderFollowUpPolicy(reminder);
  return policy.on_failure === "retry" ? policy.max_attempts : 1;
}

function reminderFollowUpBadge(reminder) {
  const followUpState = reminderFollowUpState(reminder);
  if (reminderRetryReady(reminder)) {
    return {
      status: "retry_ready",
      label: "Retry ready",
    };
  }
  if (followUpState.status === "none") {
    return null;
  }
  return {
    status: followUpState.status,
    label: humanizeLabel(followUpState.status),
  };
}

function reminderFollowUpPolicySummary(reminder) {
  const policy = reminderFollowUpPolicy(reminder);
  if (policy.on_failure !== "retry") {
    return "No automatic follow-up";
  }
  return `Retry on Telegram failure | ${policy.max_attempts} total attempt(s) | ${formatDurationSeconds(policy.retry_delay_seconds)}`;
}

function reminderFollowUpStateSummary(reminder) {
  const policy = reminderFollowUpPolicy(reminder);
  const followUpState = reminderFollowUpState(reminder);

  if (reminderRetryReady(reminder)) {
    return "Retry policy is armed before the first delivery attempt. Total attempts include the first send.";
  }
  if (followUpState.status === "retry_scheduled") {
    return `Retry ${followUpState.attempt_count} of ${policy.max_attempts} is queued for ${formatDate(followUpState.next_attempt_at)}.`;
  }
  if (followUpState.status === "snoozed") {
    return `Follow-up delivery is snoozed until ${formatDate(followUpState.next_attempt_at)}.`;
  }
  if (followUpState.status === "rescheduled") {
    return `Follow-up delivery moved to ${formatDate(followUpState.next_attempt_at)}.`;
  }
  if (followUpState.status === "dead_letter") {
    return `Retry budget exhausted after ${followUpState.attempt_count} attempt(s). Operator follow-up is required from the runtime ledger.`;
  }
  return "No automatic follow-up configured for this reminder.";
}

function sortReminderRecords(reminders) {
  const scheduled = reminders
    .filter((reminder) => reminder.status === "scheduled")
    .sort((left, right) => left.scheduled_for.localeCompare(right.scheduled_for));
  const completed = reminders
    .filter((reminder) => reminder.status !== "scheduled")
    .sort((left, right) => (reminderEventAt(right) || "").localeCompare(reminderEventAt(left) || ""));
  return [...scheduled, ...completed];
}

function reminderCountSummary(counts) {
  const labels = ["scheduled", "delivered", "failed", "canceled"];
  const summary = labels
    .filter((label) => counts[label] > 0)
    .map((label) => `${counts[label]} ${label}`);
  return summary.join(" | ") || "No reminder activity yet";
}

function summarizeReminderState() {
  const counts = {
    scheduled: 0,
    delivered: 0,
    failed: 0,
    canceled: 0,
  };
  const followUpCounts = {
    retry_scheduled: 0,
    snoozed: 0,
    rescheduled: 0,
    dead_letter: 0,
  };
  let retryReadyCount = 0;
  for (const reminder of state.reminders) {
    if (Object.prototype.hasOwnProperty.call(counts, reminder.status)) {
      counts[reminder.status] += 1;
    }
    const followUpState = reminderFollowUpState(reminder);
    if (Object.prototype.hasOwnProperty.call(followUpCounts, followUpState.status)) {
      followUpCounts[followUpState.status] += 1;
    }
    if (reminderRetryReady(reminder)) {
      retryReadyCount += 1;
    }
  }
  const orderedReminders = sortReminderRecords(state.reminders);
  const nextScheduled = orderedReminders.find((reminder) => reminder.status === "scheduled") || null;
  const recentOutcome = orderedReminders.find((reminder) => reminder.status !== "scheduled") || null;
  return {
    counts,
    followUpCounts,
    retryReadyCount,
    nextScheduled,
    recentOutcome,
  };
}

function reminderFollowUpCountSummary(summary) {
  const labels = [];
  if (summary.retryReadyCount > 0) {
    labels.push(`${summary.retryReadyCount} retry ready`);
  }
  for (const label of ["retry_scheduled", "snoozed", "rescheduled", "dead_letter"]) {
    if (summary.followUpCounts[label] > 0) {
      labels.push(`${summary.followUpCounts[label]} ${humanizeLabel(label)}`);
    }
  }
  return labels.join(" | ") || "No follow-up policy active";
}

function brokerWorkspacePath(workspaceId) {
  return `/v1/memory/broker/workspaces/${encodeURIComponent(workspaceId)}`;
}

function normalizeBrokerWorkspaceId(value) {
  const normalized = String(value || "").trim();
  return normalized || DEFAULT_BROKER_WORKSPACE_ID;
}

function rememberMemoryBrokerWorkspaceId(value) {
  state.memoryBrokerWorkspaceId = normalizeBrokerWorkspaceId(value);
  localStorage.setItem(BROKER_WORKSPACE_STORAGE_KEY, state.memoryBrokerWorkspaceId);
  elements.brokerWorkspaceIdInput.value = state.memoryBrokerWorkspaceId;
}

function parseBrokerProjectIds(rawValue) {
  return [...new Set(String(rawValue || "").split(/[\n,]/).map((value) => value.trim()).filter(Boolean))];
}

function brokerScopeSummary(projectIds) {
  return projectIds.length ? projectIds.join(", ") : "All projects in this workspace";
}

function brokerProbeResultCount(probe) {
  return Array.isArray(probe?.results) ? probe.results.length : 0;
}

function brokerProbeErrorMessage(probe) {
  return typeof probe?.error?.message === "string" && probe.error.message ? probe.error.message : null;
}

function formatBrokerResultMeta(result) {
  const detailParts = [];
  if (result.project_id) {
    detailParts.push(result.project_id);
  } else {
    detailParts.push("workspace-wide");
  }
  if (result.source_ref) {
    detailParts.push(result.source_ref);
  }
  if (typeof result.score === "number") {
    detailParts.push(`score ${result.score.toFixed(2)}`);
  }
  return detailParts.join(" | ");
}

function syncMemoryBrokerForm() {
  rememberMemoryBrokerWorkspaceId(state.memoryBrokerWorkspaceId);
  if (state.memoryBrokerState && state.memoryBrokerState.workspace_id === state.memoryBrokerWorkspaceId) {
    elements.brokerEnabledInput.checked = state.memoryBrokerState.status === "enabled";
    elements.brokerProjectIdsInput.value = (state.memoryBrokerState.scope?.project_ids || []).join(", ");
    return;
  }
  if (!elements.brokerProjectIdsInput.value) {
    elements.brokerProjectIdsInput.value = "";
  }
}

function updateMemoryBrokerControls() {
  syncMemoryBrokerForm();
  const brokerState = state.memoryBrokerState;
  const brokerEnabled = hasActiveSession() && brokerState?.status === "enabled";

  elements.brokerWorkspaceIdInput.disabled = !hasActiveSession();
  elements.brokerProjectIdsInput.disabled = !hasActiveSession();
  elements.brokerEnabledInput.disabled = !hasActiveSession();
  elements.saveBrokerButton.disabled = !hasActiveSession();
  elements.brokerQueryInput.disabled = !brokerEnabled;
  elements.brokerQueryProjectIdInput.disabled = !brokerEnabled;
  elements.probeBrokerButton.disabled = !brokerEnabled;

  if (!hasActiveSession()) {
    elements.brokerMeta.textContent = "Complete sign-in before changing workspace memory broker consent.";
    elements.brokerProbeMeta.textContent = "Broker preview remains web-only and unlocks after sign-in.";
    return;
  }

  if (!brokerState) {
    elements.brokerMeta.textContent = "Refresh or save to resolve the current workspace broker state.";
    elements.brokerProbeMeta.textContent = "Enable this workspace from web/PWA before probing the broker path.";
    return;
  }

  elements.brokerMeta.textContent =
    `Consent ${humanizeLabel(brokerState.status)} | provider ${humanizeLabel(brokerState.provider_status)} | scope ${brokerScopeSummary(brokerState.scope?.project_ids || [])}`;

  if (state.memoryBrokerProbe?.audit) {
    elements.brokerProbeMeta.textContent = `Last probe ${humanizeLabel(state.memoryBrokerProbe.audit.status)} | ${brokerProbeResultCount(state.memoryBrokerProbe)} result(s).`;
    return;
  }

  const probeError = brokerProbeErrorMessage(state.memoryBrokerProbe);
  if (probeError) {
    elements.brokerProbeMeta.textContent = `Last probe failed | ${probeError}`;
    return;
  }

  if (!brokerEnabled) {
    elements.brokerProbeMeta.textContent = "Enable this workspace from web/PWA before probing the broker path.";
    return;
  }

  if (brokerState.provider_status !== "ready") {
    elements.brokerProbeMeta.textContent = "Opt-in is stored, but this runtime still has the KG broker provider disabled.";
    return;
  }

  elements.brokerProbeMeta.textContent = "Run a web-only broker probe to record query scope and audit status.";
}

function renderMemoryBrokerProbeCard() {
  if (!state.memoryBrokerProbe) {
    return `
      <div class="empty-state">
        <h3>No broker probe yet</h3>
        <p>Save opt-in state above, then run a web-only broker probe to record provider readiness and workspace-scoped audit status.</p>
      </div>
    `;
  }

  const probeError = brokerProbeErrorMessage(state.memoryBrokerProbe);
  if (probeError) {
    return `
      <div class="checkpoint-summary broker-probe-card">
        <span class="pill" data-status="error">Probe failed</span>
        <h3>Last broker probe</h3>
        <p>The runtime rejected the broker preview request. Telegram remains summary-safe and cannot trigger this path.</p>
        <dl>
          ${kvRow("Workspace", state.memoryBrokerProbe.workspace_id || state.memoryBrokerWorkspaceId)}
          ${kvRow("Query", state.memoryBrokerProbe.query || "Not set")}
          ${kvRow("Project filter", state.memoryBrokerProbe.project_id || "Workspace-wide")}
          ${kvRow("Error", probeError)}
        </dl>
      </div>
    `;
  }

  const probe = state.memoryBrokerProbe;
  const results = Array.isArray(probe.results) ? probe.results : [];
  const resultRows = results.length
    ? results
        .map(
          (result) => `
            <li class="source-row">
              <span>${escapeHtml(result.title || humanizeLabel(result.kind))}</span>
              <span class="microcopy">${escapeHtml(formatBrokerResultMeta(result))}</span>
            </li>
          `,
        )
        .join("")
    : '<li class="source-row"><span>No scoped results</span><span class="microcopy">Provider unavailable or no matching workspace entries</span></li>';
  const providerCopy =
    probe.provider_status === "ready"
      ? `${results.length} scoped result(s) returned from the broker preview.`
      : "The provider is unavailable in this runtime, but the web-only audit trail still updated.";

  return `
    <div class="checkpoint-summary broker-probe-card">
      <span class="pill" data-status="${escapeHtml(probe.audit.status)}">${escapeHtml(humanizeLabel(probe.audit.status))}</span>
      <h3>Last broker probe</h3>
      <p>${escapeHtml(providerCopy)}</p>
      <dl>
        ${kvRow("Workspace", probe.workspace_id)}
        ${kvRow("Query", probe.query)}
        ${kvRow("Project filter", probe.project_id || "Workspace-wide")}
        ${kvRow("Provider", humanizeLabel(probe.provider))}
        ${kvRow("Provider status", humanizeLabel(probe.provider_status))}
        ${kvRow("Result count", String(results.length))}
        ${kvRow("Recorded at", formatDate(probe.audit.created_at))}
      </dl>
      <div class="source-block">
        <h4>Scoped preview</h4>
        <ul class="source-list">${resultRows}</ul>
      </div>
    </div>
  `;
}

function renderMemoryBrokerCard() {
  updateMemoryBrokerControls();

  if (!hasActiveSession()) {
    elements.brokerCard.innerHTML = `
      <div class="empty-state">
        <h3>Broker consent unlocks after sign-in</h3>
        <p>Workspace/project broker opt-in stays on the web control plane. Telegram only remains summary-safe and cannot administer this scope.</p>
      </div>
    `;
    return;
  }

  if (!state.memoryBrokerState) {
    elements.brokerCard.innerHTML = `
      <div class="empty-state">
        <h3>Waiting for broker state</h3>
        <p>Refresh the runtime or save the current workspace scope to resolve its broker consent state from assistant-api.</p>
      </div>
    `;
    return;
  }

  const brokerState = state.memoryBrokerState;
  const statusSummary =
    brokerState.status === "enabled"
      ? "This workspace has explicit web-side consent for scoped broker reads. Telegram still cannot enable or request raw broker retrieval."
      : "This workspace is still blocked from broker reads until you explicitly opt in from the web control plane.";
  const providerSummary =
    brokerState.provider_status === "ready"
      ? "This runtime can serve scoped broker previews."
      : brokerState.provider_status === "disabled"
        ? "Consent can be stored even while the KG broker provider stays disabled for this runtime."
        : "The broker provider is not fully configured in this runtime yet.";
  const consentSurface = brokerState.consent?.source_surface ? humanizeLabel(brokerState.consent.source_surface) : "Not set";
  const lastError = brokerState.last_error_code
    ? `${brokerState.last_error_code}${brokerState.last_error_message ? ` | ${brokerState.last_error_message}` : ""}`
    : "No broker error recorded";

  elements.brokerCard.innerHTML = `
    <div class="checkpoint-summary">
      <div class="broker-status-row">
        <span class="pill" data-status="${escapeHtml(brokerState.status)}">${escapeHtml(humanizeLabel(brokerState.status))}</span>
        <span class="pill" data-status="${escapeHtml(brokerState.provider_status)}">${escapeHtml(`provider ${humanizeLabel(brokerState.provider_status)}`)}</span>
      </div>
      <h3>Workspace broker state</h3>
      <p>${escapeHtml(statusSummary)}</p>
      <p class="microcopy">${escapeHtml(providerSummary)}</p>
      <dl>
        ${kvRow("Workspace", brokerState.workspace_id)}
        ${kvRow("Project scope", brokerScopeSummary(brokerState.scope?.project_ids || []))}
        ${kvRow("Provider", humanizeLabel(brokerState.provider))}
        ${kvRow("Consent source", consentSurface)}
        ${kvRow("Granted", formatDate(brokerState.consent?.granted_at))}
        ${kvRow("Revoked", formatDate(brokerState.consent?.revoked_at))}
        ${kvRow("Updated", formatDate(brokerState.consent?.updated_at))}
        ${kvRow("Last brokered", formatDate(brokerState.last_brokered_at))}
        ${kvRow("Last audit", brokerState.last_audit_id || "Not recorded")}
        ${kvRow("Last error", lastError)}
      </dl>
    </div>
    ${renderMemoryBrokerProbeCard()}
  `;
}

function renderSessionCard() {
  if (!state.session) {
    elements.sessionCard.innerHTML = `
      <div class="empty-state">
        <h3>Connect to unlock memory and resume</h3>
        <p>The shell already knows the assistant-api shape. Sign in to read the active session, memory items, and the latest checkpoint.</p>
      </div>
    `;
    return;
  }

  const provider = state.session.provider;
  const session = state.session.session;
  const authState = state.session.auth_state;
  elements.sessionCard.innerHTML = `
    <span class="pill" data-status="${escapeHtml(authState)}">${escapeHtml(authState.replaceAll("_", " "))}</span>
    <dl>
      ${kvRow("User", state.session.user_id)}
      ${kvRow("Device session", state.session.device_session_id)}
      ${kvRow("Provider subject", provider.provider_subject)}
      ${kvRow("Scopes", provider.scopes.join(", ") || "None")}
      ${kvRow("Connected at", formatDate(provider.connected_at))}
      ${kvRow("Expires", formatDate(session.expires_at))}
      ${kvRow("Last seen", formatDate(session.last_seen_at))}
    </dl>
    ${
      hasActiveSession()
        ? ""
        : '<p class="microcopy">Complete the provider callback to unlock memory write and checkpoint sync.</p>'
    }
  `;
}

function renderTelegramCard() {
  if (!hasActiveSession()) {
    elements.telegramCard.innerHTML = `
      <div class="empty-state">
        <h3>Link Telegram after sign-in</h3>
        <p>The companion surface only becomes available after the first-party session is active on the web shell.</p>
      </div>
    `;
    return;
  }

  if (!state.telegramLink) {
    elements.telegramCard.innerHTML = `
      <div class="empty-state">
        <h3>Waiting for Telegram state</h3>
        <p>Refresh the runtime to read the current Telegram companion status from assistant-api.</p>
      </div>
    `;
    return;
  }

  const linkState = state.telegramLink;
  const reminderSummary = summarizeReminderState();
  const status = linkState.status || "not_linked";
  const linkLabel =
    status === "pending" ? "Reissue Telegram Link" : status === "error" ? "Try Telegram Link Again" : "Start Telegram Link";
  const summary =
    status === "linked"
      ? "Telegram is linked as a companion surface. Sensitive setup, broker consent, and full memory control still stay on web/PWA."
      : status === "pending"
        ? "A short-lived code is ready. Use the code or deep link in Telegram. The hidden completion route remains smoke-only."
        : status === "error"
          ? "The last Telegram link attempt failed. Reissue a short-lived code from the web shell."
          : "Issue a short-lived Telegram code from the web shell, then complete the companion binding on Telegram.";
  const actionRow =
    status === "linked"
      ? ""
      : `
        <div class="cluster">
          <button class="button button-strong" type="button" data-telegram-action="start">${escapeHtml(linkLabel)}</button>
          ${
            linkState.bot_deep_link
              ? `<a class="inline-link" href="${escapeHtml(linkState.bot_deep_link)}" target="_blank" rel="noreferrer">Open bot deep link</a>`
              : ""
          }
        </div>
      `;
  const codeRow = linkState.link_code
    ? `<p class="microcopy">Link code <span class="mono">${escapeHtml(linkState.link_code)}</span></p>`
    : "";
  const errorRow =
    linkState.last_error_code || linkState.last_error_message
      ? `<p class="microcopy">Last error ${escapeHtml(linkState.last_error_code || "unknown")} | ${escapeHtml(linkState.last_error_message || "No message")}</p>`
      : "";

  elements.telegramCard.innerHTML = `
    <div class="checkpoint-summary">
      <span class="pill" data-status="${escapeHtml(status)}">${escapeHtml(humanizeLabel(status))}</span>
      <h3>Telegram companion</h3>
      <p>${escapeHtml(summary)}</p>
      <dl>
        ${kvRow("Surface", linkState.surface || "telegram")}
        ${kvRow("Display name", linkState.telegram_display_name || "Not linked yet")}
        ${kvRow("Username", linkState.telegram_username ? `@${linkState.telegram_username}` : "Not linked yet")}
        ${kvRow("Expires", formatDate(linkState.expires_at))}
        ${kvRow("Linked at", formatDate(linkState.linked_at))}
        ${kvRow("Last event", formatDate(linkState.last_event_at))}
        ${kvRow("Resume token", linkState.last_resume_token_ref || "Not set")}
        ${kvRow("Workspace broker", "Web-only control")}
        ${kvRow("Reminder queue", reminderCountSummary(reminderSummary.counts))}
        ${kvRow("Follow-up watch", reminderFollowUpCountSummary(reminderSummary))}
        ${kvRow("Next reminder", reminderSummary.nextScheduled ? formatDate(reminderSummary.nextScheduled.scheduled_for) : "No scheduled reminder")}
        ${kvRow("Last reminder", reminderSummary.recentOutcome ? humanizeLabel(reminderSummary.recentOutcome.status) : "No reminder outcome yet")}
      </dl>
      ${actionRow}
      ${codeRow}
      ${errorRow}
    </div>
  `;
}

function renderCheckpointContinuity() {
  if (!hasActiveSession()) {
    elements.checkpointContinuity.innerHTML = `
      <h3>Continuity metadata</h3>
      <p>Complete sign-in before the shell can read surface handoff metadata from the runtime checkpoint.</p>
    `;
    return;
  }

  const checkpoint = state.checkpointDraft || state.checkpoint;
  if (!checkpoint) {
    elements.checkpointContinuity.innerHTML = `
      <h3>Continuity metadata</h3>
      <p>No checkpoint metadata is available yet. Once a checkpoint is synced, the shell will show its last surface handoff.</p>
    `;
    return;
  }

  const summary = state.checkpointDirty
    ? "The local draft is carrying continuity metadata that will be written on the next checkpoint sync."
    : "This summary reflects the latest checkpoint continuity metadata returned by assistant-api.";

  elements.checkpointContinuity.innerHTML = `
    <span class="pill" data-status="${escapeHtml(checkpoint.handoff_kind || "none")}">${escapeHtml(humanizeLabel(checkpoint.handoff_kind || "none"))}</span>
    <h3>Continuity metadata</h3>
    <p>${escapeHtml(summary)}</p>
    <dl>
      ${kvRow("Current surface", humanizeLabel(checkpoint.surface || "web"))}
      ${kvRow("Handoff kind", humanizeLabel(checkpoint.handoff_kind || "none"))}
      ${kvRow("Resume token", checkpoint.resume_token_ref || "Not set")}
      ${kvRow("Last surface at", formatDate(checkpoint.last_surface_at))}
    </dl>
  `;
}

function renderCheckpointCard() {
  if (!hasActiveSession()) {
    state.checkpointConflict = null;
    applyCheckpointDraftToForm();
    updateCheckpointMeta();
    renderCheckpointConflict();
    renderCheckpointContinuity();
    return;
  }
  applyCheckpointDraftToForm();
  updateCheckpointMeta();
  renderCheckpointConflict();
  renderCheckpointContinuity();
}

function renderRemindersMeta() {
  ensureReminderDefaults();
  const telegramLinked = state.telegramLink?.status === "linked";
  const formDisabled = !hasActiveSession() || !telegramLinked;
  elements.reminderAtInput.disabled = formDisabled;
  elements.reminderMessageInput.disabled = formDisabled;
  elements.reminderFollowUpActionInput.disabled = formDisabled;
  elements.saveReminderButton.disabled = formDisabled;
  updateReminderFollowUpControls(formDisabled);

  if (!hasActiveSession()) {
    elements.remindersMeta.textContent = "Complete sign-in before scheduling reminder delivery.";
    return;
  }
  if (!telegramLinked) {
    elements.remindersMeta.textContent = "Link Telegram before scheduling reminder delivery from the web control plane.";
    return;
  }
  const summary = summarizeReminderState();
  elements.remindersMeta.textContent =
    `Delivery stays on Telegram. ${reminderCountSummary(summary.counts)}. ` +
    "Follow-up policy stays on the web control plane, and new reminders inherit the current conversation context in the runtime audit trail.";
}

function renderRemindersCard() {
  if (!hasActiveSession()) {
    elements.remindersCard.innerHTML = `
      <div class="empty-state">
        <h3>Reminder control unlocks after sign-in</h3>
        <p>The web shell can only schedule or inspect Telegram reminder delivery after the first-party session is active.</p>
      </div>
    `;
    return;
  }

  const telegramLinked = state.telegramLink?.status === "linked";
  if (!state.reminders.length) {
    elements.remindersCard.innerHTML = `
      <div class="empty-state">
        <h3>No reminder activity yet</h3>
        <p>${
          telegramLinked
            ? "Schedule a Telegram reminder above. Optional retry follow-up stays visible in the runtime ledger immediately."
            : "Link Telegram first, then the control plane can schedule reminder delivery."
        }</p>
      </div>
    `;
    return;
  }

  const summary = summarizeReminderState();
  const reminderRows = sortReminderRecords(state.reminders)
    .map((reminder) => {
      const followUpState = reminderFollowUpState(reminder);
      const followUpBadge = reminderFollowUpBadge(reminder);
      const detailLine =
        reminder.status === "failed"
          ? `Last error ${reminder.last_error_code || "unknown"} | ${reminder.last_error_message || "No message"}`
          : reminder.status === "delivered"
            ? `Delivered through Telegram at ${formatDate(reminder.delivered_at)}.`
            : reminder.status === "canceled"
              ? `Canceled at ${formatDate(reminder.canceled_at)}.`
              : `Queued for Telegram delivery at ${formatDate(reminder.scheduled_for)}.`;
      const actionRow =
        reminder.status === "scheduled"
          ? `<button class="button" type="button" data-reminder-action="cancel" data-reminder-id="${escapeHtml(reminder.reminder_id)}">Cancel Reminder</button>`
          : '<span class="microcopy">Runtime audit remains available in the ledger below.</span>';
      return `
        <article class="reminder-item">
          <div class="reminder-headline">
            <h3>${escapeHtml(reminderMessage(reminder))}</h3>
            <div class="reminder-status-pills">
              <span class="pill" data-status="${escapeHtml(reminder.status)}">${escapeHtml(humanizeLabel(reminder.status))}</span>
              ${
                followUpBadge
                  ? `<span class="pill" data-status="${escapeHtml(followUpBadge.status)}">${escapeHtml(followUpBadge.label)}</span>`
                  : ""
              }
            </div>
          </div>
          <dl>
            ${kvRow("Reminder ID", reminder.reminder_id)}
            ${kvRow("Runtime job", reminder.job_id)}
            ${kvRow("Channel", humanizeLabel(reminder.channel || "telegram"))}
            ${kvRow("Scheduled for", formatDate(reminder.scheduled_for))}
            ${kvRow("Follow-up policy", reminderFollowUpPolicySummary(reminder))}
            ${kvRow("Follow-up state", humanizeLabel(followUpState.status))}
            ${kvRow("Attempt budget", `${followUpState.attempt_count} / ${reminderAttemptBudget(reminder)}`)}
            ${kvRow("Next attempt", formatDate(followUpState.next_attempt_at))}
            ${kvRow(reminderEventLabel(reminder), formatDate(reminderEventAt(reminder)))}
          </dl>
          <p class="microcopy reminder-meta">${escapeHtml(detailLine)}</p>
          <p class="microcopy reminder-meta">${escapeHtml(reminderFollowUpStateSummary(reminder))}</p>
          <div class="reminder-actions">
            ${actionRow}
          </div>
        </article>
      `;
    })
    .join("");

  elements.remindersCard.innerHTML = `
    <div class="reminder-summary">
      <h3>Reminder summary</h3>
      <p>${
        telegramLinked
          ? "Telegram-linked reminder delivery is live on this control plane."
          : "Reminder history is still visible, but new scheduling is blocked until Telegram is linked again."
      }</p>
      <dl>
        ${kvRow("Queue", reminderCountSummary(summary.counts))}
        ${kvRow("Follow-up watch", reminderFollowUpCountSummary(summary))}
        ${kvRow("Next reminder", summary.nextScheduled ? formatDate(summary.nextScheduled.scheduled_for) : "No scheduled reminder")}
        ${kvRow("Last outcome", summary.recentOutcome ? humanizeLabel(summary.recentOutcome.status) : "No reminder outcome yet")}
      </dl>
    </div>
    <div class="reminder-list">${reminderRows}</div>
  `;
}

function renderMemoryExportMeta() {
  elements.exportMemoryButton.disabled = !hasActiveSession();
  if (!state.lastMemoryExport) {
    elements.memoryExportMeta.textContent = "Exports include provenance and revision history.";
    return;
  }
  elements.memoryExportMeta.textContent = `Last export ${state.lastMemoryExport.export_id} | ${state.lastMemoryExport.item_count} items | expires ${formatDate(state.lastMemoryExport.expires_at)}`;
}

function memoryActionButton(label, action, id, tone = "") {
  return `<button class="button ${tone}" type="button" data-memory-action="${escapeHtml(action)}" data-memory-id="${escapeHtml(id)}">${escapeHtml(label)}</button>`;
}

function renderMemorySources(item) {
  if (!item.sources || !item.sources.length) {
    return '<li class="source-row"><span>No provenance stored yet</span><span class="microcopy">Operator follow-up needed</span></li>';
  }
  return item.sources
    .map(
      (source) => `
        <li class="source-row">
          <span>${escapeHtml(source.conversation_id)}${source.message_id ? ` | ${escapeHtml(source.message_id)}` : ""}</span>
          <span class="microcopy">${escapeHtml(source.note || formatDate(source.captured_at))}</span>
        </li>
      `,
    )
    .join("");
}

function renderMemoryList() {
  if (!hasActiveSession()) {
    elements.memoryList.innerHTML = `
      <div class="empty-state">
        <h3>Memory control stays opt-in</h3>
        <p>After active sign-in you can create a memory item, mark its importance, and decide whether it belongs in the next checkpoint.</p>
      </div>
    `;
    return;
  }

  if (!state.memoryItems.length) {
    elements.memoryList.innerHTML = `
      <div class="empty-state">
        <h3>No memory saved yet</h3>
        <p>Write one explicit memory above. Each item now carries provenance so the source of truth stays inspectable.</p>
      </div>
    `;
    return;
  }

  elements.memoryList.innerHTML = state.memoryItems
    .map((item) => {
      const selected = state.selectedMemoryIds.has(item.id) ? "checked" : "";
      const canResume = item.status === "active";
      const actionRow =
        item.status === "deleted"
          ? '<span class="microcopy">Deleted items stay out of retrieval and checkpoint sync while purge is pending.</span>'
          : `
            ${item.status === "active" ? memoryActionButton("Archive", "archive", item.id) : ""}
            ${memoryActionButton("Delete", "delete", item.id)}
          `;
      return `
        <article class="memory-item">
          <div class="memory-headline">
            <span class="pill" data-status="${escapeHtml(item.status)}">${escapeHtml(item.kind)} | ${escapeHtml(item.status)}</span>
            <label class="memory-checkbox">
              <input type="checkbox" data-memory-select="${escapeHtml(item.id)}" ${selected} ${canResume ? "" : "disabled"} />
              Include in checkpoint
            </label>
          </div>
          <p class="memory-content">${escapeHtml(item.content)}</p>
          <div class="memory-meta">
            <span class="microcopy">Importance ${escapeHtml(String(item.importance))} | source ${escapeHtml(item.source_type)}</span>
            <span class="microcopy">Created ${escapeHtml(formatDate(item.created_at))} | updated ${escapeHtml(formatDate(item.updated_at))}</span>
          </div>
          <div class="source-block">
            <h4>Provenance</h4>
            <ul class="source-list">${renderMemorySources(item)}</ul>
          </div>
          <div class="memory-actions">
            ${actionRow}
          </div>
        </article>
      `;
    })
    .join("");
}

function formatJobDetailValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not set";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

function jobDetailEntries(job) {
  const entries = [];
  for (const [key, value] of Object.entries(job.details || {})) {
    if (
      ["payload", "follow_up_policy", "follow_up_state"].includes(key) &&
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      for (const [nestedKey, nestedValue] of Object.entries(value)) {
        entries.push([`${key}_${nestedKey}`, nestedValue]);
      }
      continue;
    }
    entries.push([key, value]);
  }
  return entries;
}

function renderJobDetails(job) {
  const entries = jobDetailEntries(job);
  if (!entries.length) {
    return '<li class="detail-row"><span>No details yet</span><span class="microcopy">Runtime producer update required</span></li>';
  }
  return entries
    .map(
      ([key, value]) => `
        <li class="detail-row">
          <span>${escapeHtml(humanizeLabel(key))}</span>
          <span class="microcopy">${escapeHtml(formatJobDetailValue(value))}</span>
        </li>
      `,
    )
    .join("");
}

function renderJobsCard() {
  if (!hasActiveSession()) {
    elements.jobsCard.innerHTML = `
      <div class="empty-state">
        <h3>Job audit trail appears after sign-in</h3>
        <p>Export, delete, and reminder jobs are only listed once the runtime can resolve the current user.</p>
      </div>
    `;
    return;
  }

  if (!state.runtimeJobs.length) {
    elements.jobsCard.innerHTML = `
      <div class="empty-state">
        <h3>No auditable jobs yet</h3>
        <p>Memory export, delete, and reminder actions will show up here with surface, conversation, and runtime detail metadata.</p>
      </div>
    `;
    return;
  }

  const jobRows = state.runtimeJobs
    .map((job) => {
      const attemptCount = Number.isInteger(job.attempt_count) ? job.attempt_count : 0;
      return `
        <article class="job-row">
          <div class="job-headline">
            <h3>${escapeHtml(humanizeLabel(job.kind))}</h3>
            <span class="pill" data-status="${escapeHtml(job.status)}">${escapeHtml(humanizeLabel(job.status))}</span>
          </div>
          <dl>
            ${kvRow("Job ID", job.job_id)}
            ${kvRow("Requested", formatDate(job.requested_at))}
            ${kvRow("Available", formatDate(job.available_at))}
            ${kvRow("Started", formatDate(job.started_at))}
            ${kvRow("Completed", formatDate(job.completed_at))}
            ${kvRow("Attempts", String(attemptCount))}
            ${kvRow("Resource", job.resource_id || "Not set")}
            ${kvRow("Audit surface", humanizeLabel(job.audit?.surface || "web"))}
            ${kvRow("Conversation", job.audit?.conversation_id || "Not set")}
          </dl>
          <ul class="detail-list">${renderJobDetails(job)}</ul>
        </article>
      `;
    })
    .join("");

  elements.jobsCard.innerHTML = `<div class="jobs-list">${jobRows}</div>`;
}

function trustFallbackHeadline(status) {
  switch (status) {
    case "pass":
      return "Release evidence is current for this build.";
    case "warn":
      return "Some release evidence is incomplete for this build.";
    case "fail":
      return "Validation failed for this build.";
    case "blocked":
      return "Release evidence is blocked right now.";
    case "invalid":
      return "Release evidence is not trustworthy yet.";
    case "stale":
      return "This summary is older than the current repo state.";
    default:
      return "Release evidence is still being gathered.";
  }
}

function trustFallbackGuidance(status) {
  switch (status) {
    case "pass":
      return "Use the public evidence links below if you need the release checklist or operator-facing proof trail.";
    case "warn":
      return "Use the public evidence links below before relying on this build as release-ready.";
    case "fail":
      return "Do not use this bundle as release sign-off until the failing stage is rerun and cleared.";
    case "blocked":
      return "An operator still needs to complete the missing release evidence before sign-off.";
    case "invalid":
      return "Re-run release validation before treating this summary as a trustworthy signal.";
    case "stale":
      return "Re-run release validation before using this bundle as release sign-off.";
    default:
      return "Wait for a fresh evidence summary before using this surface for release decisions.";
  }
}

function renderTrustCard() {
  if (!state.trust) {
    elements.trustCard.innerHTML = `
      <div class="empty-state">
        <h3>Waiting for evidence summary</h3>
        <p>The shell only renders the public evidence_summary contract. No raw Ralph Loop artifact paths or logs are surfaced here.</p>
      </div>
    `;
    return;
  }

  const summary = state.trust.summary;
  const fallbackHeadline = trustFallbackHeadline(summary.overall_status);
  const fallbackGuidance = trustFallbackGuidance(summary.overall_status);
  const stageRows = summary.stage_statuses
    .map(
      (stage) => `
        <li class="stage-row">
          <span>${escapeHtml(stage.stage_id)}</span>
          <span class="pill" data-status="${escapeHtml(stage.status)}">${escapeHtml(stage.status)} | ${stage.computed_score}/${stage.max_score}</span>
        </li>
      `,
    )
    .join("");
  const linkRows = summary.public_evidence_links
    .map(
      (link) => `
        <li class="trust-link-row">
          <span>${escapeHtml(link.label)}</span>
          <a href="${escapeHtml(link.url)}" target="_blank" rel="noreferrer">Open link</a>
        </li>
      `,
    )
    .join("");

  elements.trustCard.innerHTML = `
    <div class="trust-summary">
      <span class="pill" data-status="${escapeHtml(summary.overall_status)}">${escapeHtml(summary.trust_label)}</span>
      <h3>${escapeHtml(summary.bundle_id)}</h3>
      <p>${escapeHtml(fallbackHeadline)}</p>
      <p class="microcopy">${escapeHtml(fallbackGuidance)}</p>
      <p>${escapeHtml(summary.highlights.join(" "))}</p>
      <div class="score-display">
        <strong>${summary.score.total}</strong>
        <span>/ ${summary.score.max}</span>
      </div>
      <dl>
        ${kvRow("App version", state.trust.app_version)}
        ${kvRow("Generated", formatDate(summary.generated_at))}
        ${kvRow("Release channel", summary.release_channel)}
        ${kvRow("Evidence ref", state.trust.evidence_ref.bundle_id)}
      </dl>
    </div>
    <div class="stage-list">
      <h3>Stage status</h3>
      <ul>${stageRows}</ul>
    </div>
    <div class="trust-links">
      <h3>Public evidence links</h3>
      <ul>${linkRows || '<li class="trust-link-row"><span>No public links yet</span><span class="microcopy">Operator update required</span></li>'}</ul>
    </div>
  `;
}

function renderAll() {
  renderSessionCard();
  renderTelegramCard();
  renderRemindersMeta();
  renderRemindersCard();
  renderCheckpointCard();
  renderMemoryExportMeta();
  renderMemoryList();
  renderMemoryBrokerCard();
  renderJobsCard();
  renderTrustCard();
  elements.apiBaseInput.value = state.apiBase;
  setRuntimeMeta(`API ${state.apiBase} | cache ${CACHE_DB_NAME}`);
}

async function refreshSession() {
  try {
    state.session = await fetchJson("/v1/auth/session");
    await cacheWrite("session", state.session);
  } catch (error) {
    if (error.status === 401) {
      state.session = null;
      await cacheWrite("session", null);
      return;
    }
    throw error;
  }
}

async function refreshMemory() {
  if (!hasActiveSession()) {
    state.memoryItems = [];
    await cacheWrite("memory", []);
    return;
  }
  const payload = await fetchJson("/v1/memory/items?limit=30");
  state.memoryItems = payload.items || [];
  const activeSelections = new Set(
    state.memoryItems.filter((item) => item.status === "active").map((item) => item.id),
  );
  state.selectedMemoryIds = new Set(
    [...state.selectedMemoryIds].filter((memoryId) => activeSelections.has(memoryId)),
  );
  if (state.checkpointDraft) {
    state.checkpointDraft.selected_memory_ids = [...state.selectedMemoryIds];
    await persistCheckpointDraft();
  }
  await cacheWrite("memory", state.memoryItems);
}

async function refreshMemoryBroker() {
  if (!hasActiveSession()) {
    state.memoryBrokerState = null;
    state.memoryBrokerProbe = null;
    await Promise.all([cacheWrite("memory_broker_state", null), cacheWrite("memory_broker_probe", null)]);
    return;
  }

  const workspaceId = normalizeBrokerWorkspaceId(state.memoryBrokerWorkspaceId);
  rememberMemoryBrokerWorkspaceId(workspaceId);
  if (state.memoryBrokerProbe?.workspace_id && state.memoryBrokerProbe.workspace_id !== workspaceId) {
    state.memoryBrokerProbe = null;
    await cacheWrite("memory_broker_probe", null);
  }
  state.memoryBrokerState = await fetchJson(brokerWorkspacePath(workspaceId));
  await cacheWrite("memory_broker_state", state.memoryBrokerState);
}

async function refreshTelegramLink() {
  if (!hasActiveSession()) {
    state.telegramLink = null;
    await cacheWrite("telegram_link", null);
    return;
  }
  state.telegramLink = await fetchJson("/v1/surfaces/telegram/link");
  await cacheWrite("telegram_link", state.telegramLink);
}

async function refreshReminders() {
  if (!hasActiveSession()) {
    state.reminders = [];
    await cacheWrite("reminders", []);
    return;
  }
  const payload = await fetchJson("/v1/reminders?limit=10");
  state.reminders = payload.items || [];
  await cacheWrite("reminders", state.reminders);
}

async function refreshCheckpoint() {
  if (!hasActiveSession()) {
    state.checkpoint = null;
    state.checkpointDraft = null;
    state.checkpointDirty = false;
    state.checkpointConflict = null;
    state.selectedMemoryIds = new Set();
    await persistCheckpointDraft();
    return;
  }
  try {
    const serverCheckpoint = await fetchJson("/v1/checkpoints/current");
    state.checkpoint = serverCheckpoint;
    if (!state.checkpointDraft || !state.checkpointDirty) {
      state.checkpointDraft = cloneJson(serverCheckpoint);
      state.checkpointDirty = false;
      state.checkpointConflict = null;
    } else if (!checkpointsDiffer(state.checkpointDraft, serverCheckpoint)) {
      state.checkpointDraft = cloneJson(serverCheckpoint);
      state.checkpointDirty = false;
      state.checkpointConflict = null;
    } else {
      state.checkpointConflict = {
        server: cloneJson(serverCheckpoint),
        local: cloneJson(state.checkpointDraft),
      };
    }
    state.selectedMemoryIds = new Set((state.checkpointDraft || serverCheckpoint).selected_memory_ids || []);
    await persistCheckpointDraft();
  } catch (error) {
    if (error.status === 404) {
      state.checkpoint = null;
      state.checkpointConflict = null;
      if (!state.checkpointDirty) {
        state.checkpointDraft = null;
        state.selectedMemoryIds = new Set();
      }
      await persistCheckpointDraft();
      return;
    }
    throw error;
  }
}

async function refreshJobs() {
  if (!hasActiveSession()) {
    state.runtimeJobs = [];
    await cacheWrite("runtime_jobs", []);
    return;
  }
  const payload = await fetchJson("/v1/jobs?limit=10");
  state.runtimeJobs = payload.items || [];
  await cacheWrite("runtime_jobs", state.runtimeJobs);
}

async function refreshTrust() {
  try {
    state.trust = await fetchJson("/v1/trust/current");
    await cacheWrite("trust", state.trust);
  } catch (error) {
    if (error.status === 404) {
      state.trust = null;
      await cacheWrite("trust", null);
      return;
    }
    throw error;
  }
}

async function refreshAll() {
  try {
    setNotice("Refreshing runtime...");
    await refreshTrust();
    await refreshSession();
    await Promise.all([
      refreshTelegramLink(),
      refreshReminders(),
      refreshMemory(),
      refreshMemoryBroker(),
      refreshCheckpoint(),
      refreshJobs(),
    ]);
    renderAll();
    setNotice("Runtime synced.");
  } catch (error) {
    setNotice(error.message || "Failed to refresh runtime.", "error");
  }
}

async function startAuth() {
  const payload = {
    redirect_uri: appReturnUrl(),
    device_label: inferDeviceLabel(),
    platform: inferPlatform(),
  };
  try {
    setNotice("Requesting provider redirect...");
    const start = await fetchJson("/v1/auth/openai/start", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    window.location.assign(start.authorization_url);
  } catch (error) {
    setNotice(error.message || "Failed to start auth handshake.", "error");
  }
}

async function saveCheckpoint(event, { force = false } = {}) {
  if (event) {
    event.preventDefault();
  }
  if (!hasActiveSession()) {
    setNotice("Sign in before saving a checkpoint.", "error");
    return;
  }
  try {
    const payload = {
      ...buildCheckpointDraftFromForm(nextCheckpointVersion()),
      base_version: state.checkpoint ? state.checkpoint.version : null,
      force,
    };
    const storedCheckpoint = await fetchJson("/v1/checkpoints/current", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    state.checkpoint = storedCheckpoint;
    state.checkpointDraft = cloneJson(storedCheckpoint);
    state.checkpointDirty = false;
    state.checkpointConflict = null;
    state.selectedMemoryIds = new Set(storedCheckpoint.selected_memory_ids || []);
    await persistCheckpointDraft();
    renderCheckpointCard();
    renderMemoryList();
    setNotice(force ? "Local draft replaced the server checkpoint." : "Checkpoint synced.");
  } catch (error) {
    if (error.status === 409 && error.payload && error.payload.code === "checkpoint_conflict") {
      state.checkpoint = error.payload.server_checkpoint;
      state.checkpointDraft = error.payload.client_checkpoint;
      state.checkpointDirty = true;
      state.checkpointConflict = {
        server: cloneJson(error.payload.server_checkpoint),
        local: cloneJson(error.payload.client_checkpoint),
      };
      await persistCheckpointDraft();
      renderCheckpointCard();
      setNotice(error.message || "Checkpoint conflict detected.", "error");
      return;
    }
    setNotice(error.message || "Failed to save checkpoint.", "error");
  }
}

async function captureCheckpointDraft() {
  if (!hasActiveSession()) {
    return;
  }
  state.checkpointDraft = buildCheckpointDraftFromForm(state.checkpointDraft?.version || state.checkpoint?.version || 1);
  state.checkpointDirty = true;
  await persistCheckpointDraft();
  updateCheckpointMeta();
  renderCheckpointContinuity();
}

async function saveMemory(event) {
  event.preventDefault();
  if (!hasActiveSession()) {
    setNotice("Sign in before saving a memory item.", "error");
    return;
  }
  const content = elements.memoryContentInput.value.trim();
  if (!content) {
    setNotice("Memory content cannot be empty.", "error");
    return;
  }
  const now = new Date().toISOString();
  const memoryId = `memory_${Date.now().toString(36)}`;
  const conversationId = elements.conversationIdInput.value.trim() || `manual_${state.session.device_session_id}`;
  const messageId = elements.lastMessageIdInput.value.trim() || null;
  const route = elements.routeInput.value.trim() || DEFAULT_ROUTE;
  const sourceNote = elements.memorySourceNoteInput.value.trim();
  const payload = {
    id: memoryId,
    user_id: state.session.user_id,
    kind: elements.memoryKindInput.value,
    content,
    status: "active",
    importance: Number(elements.memoryImportanceInput.value || "70"),
    source_type: "manual_input",
    created_at: now,
    updated_at: now,
    last_used_at: null,
    sources: [
      {
        memory_id: memoryId,
        conversation_id: conversationId,
        message_id: messageId,
        note: sourceNote || `Captured from ${route}`,
        captured_at: now,
      },
    ],
  };
  try {
    await fetchJson("/v1/memory/items", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    elements.memoryContentInput.value = "";
    elements.memorySourceNoteInput.value = "";
    await refreshMemory();
    renderMemoryList();
    setNotice("Memory saved with provenance.");
  } catch (error) {
    setNotice(error.message || "Failed to save memory.", "error");
  }
}

async function patchMemory(memoryId, patch) {
  return fetchJson(`/v1/memory/items/${memoryId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

async function removeMemory(memoryId) {
  return fetchJson(`/v1/memory/items/${memoryId}`, {
    method: "DELETE",
  });
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

async function exportMemory() {
  if (!hasActiveSession()) {
    setNotice("Sign in before exporting memory.", "error");
    return;
  }
  try {
    setNotice("Preparing memory export...");
    const exportBundle = await fetchJson("/v1/memory/exports", {
      method: "POST",
    });
    state.lastMemoryExport = exportBundle;
    await cacheWrite("memory_export", exportBundle);
    await refreshJobs();
    renderMemoryExportMeta();
    renderJobsCard();
    downloadJson(exportBundle.suggested_filename, exportBundle);
    setNotice(`Export ready with ${exportBundle.item_count} item(s).`);
  } catch (error) {
    setNotice(error.message || "Failed to export memory.", "error");
  }
}

async function startTelegramLink() {
  if (!hasActiveSession()) {
    setNotice("Sign in before linking Telegram.", "error");
    return;
  }
  try {
    setNotice("Issuing Telegram link...");
    state.telegramLink = await fetchJson("/v1/surfaces/telegram/link", {
      method: "POST",
    });
    await cacheWrite("telegram_link", state.telegramLink);
    renderTelegramCard();
    renderRemindersMeta();
    renderRemindersCard();
    setNotice(state.telegramLink.status === "linked" ? "Telegram is already linked." : "Telegram link ready.");
  } catch (error) {
    setNotice(error.message || "Failed to start Telegram link.", "error");
  }
}

async function saveMemoryBrokerScope(event) {
  event.preventDefault();
  if (!hasActiveSession()) {
    setNotice("Sign in before changing workspace broker consent.", "error");
    return;
  }

  const workspaceId = normalizeBrokerWorkspaceId(elements.brokerWorkspaceIdInput.value);
  const projectIds = parseBrokerProjectIds(elements.brokerProjectIdsInput.value);
  rememberMemoryBrokerWorkspaceId(workspaceId);

  try {
    setNotice("Saving broker scope...");
    state.memoryBrokerState = await fetchJson(brokerWorkspacePath(workspaceId), {
      method: "PUT",
      body: JSON.stringify({
        enabled: elements.brokerEnabledInput.checked,
        project_ids: projectIds,
        source_surface: "web",
      }),
    });
    state.memoryBrokerProbe = null;
    await Promise.all([cacheWrite("memory_broker_state", state.memoryBrokerState), cacheWrite("memory_broker_probe", null)]);
    renderMemoryBrokerCard();
    if (state.memoryBrokerState.status === "enabled" && state.memoryBrokerState.provider_status !== "ready") {
      setNotice("Broker scope saved. Provider is still unavailable in this runtime.");
      return;
    }
    setNotice(
      state.memoryBrokerState.status === "enabled" ? "Broker scope saved." : "Broker scope saved in the disabled state.",
    );
  } catch (error) {
    setNotice(error.message || "Failed to save workspace broker scope.", "error");
  }
}

async function probeMemoryBroker() {
  if (!hasActiveSession()) {
    setNotice("Sign in before probing the workspace broker.", "error");
    return;
  }
  if (state.memoryBrokerState?.status !== "enabled") {
    setNotice("Enable the workspace broker before running a probe.", "error");
    return;
  }

  const workspaceId = normalizeBrokerWorkspaceId(elements.brokerWorkspaceIdInput.value);
  const query = elements.brokerQueryInput.value.trim();
  const projectId = elements.brokerQueryProjectIdInput.value.trim() || null;
  if (!query) {
    setNotice("Enter a broker probe query.", "error");
    return;
  }

  rememberMemoryBrokerWorkspaceId(workspaceId);

  try {
    setNotice("Probing workspace broker...");
    state.memoryBrokerProbe = await fetchJson(`${brokerWorkspacePath(workspaceId)}/query`, {
      method: "POST",
      body: JSON.stringify({
        query,
        project_id: projectId,
        limit: 5,
        source_surface: "web",
      }),
    });
    await cacheWrite("memory_broker_probe", state.memoryBrokerProbe);
    await refreshMemoryBroker();
    renderMemoryBrokerCard();
    const providerOutcome =
      state.memoryBrokerProbe.provider_status === "ready"
        ? `${brokerProbeResultCount(state.memoryBrokerProbe)} scoped result(s)`
        : "provider unavailable";
    setNotice(`Broker probe recorded with ${providerOutcome}.`);
  } catch (error) {
    state.memoryBrokerProbe = {
      workspace_id: workspaceId,
      query,
      project_id: projectId,
      error: {
        message: error.message || "Failed to probe workspace broker.",
        status: error.status || null,
      },
    };
    await cacheWrite("memory_broker_probe", state.memoryBrokerProbe);
    renderMemoryBrokerCard();
    setNotice(error.message || "Failed to probe workspace broker.", "error");
  }
}

async function handleMemoryBrokerWorkspaceChange() {
  const workspaceId = normalizeBrokerWorkspaceId(elements.brokerWorkspaceIdInput.value);
  rememberMemoryBrokerWorkspaceId(workspaceId);
  state.memoryBrokerState = null;
  state.memoryBrokerProbe = null;
  await Promise.all([cacheWrite("memory_broker_state", null), cacheWrite("memory_broker_probe", null)]);
  renderMemoryBrokerCard();
}

function reminderInputToIso(value) {
  const reminderAt = new Date(value);
  if (Number.isNaN(reminderAt.getTime())) {
    return null;
  }
  return reminderAt.toISOString();
}

function parseReminderPolicyInteger(rawValue, { min, max }) {
  const value = Number.parseInt(String(rawValue || "").trim(), 10);
  if (!Number.isInteger(value) || value < min || value > max) {
    return null;
  }
  return value;
}

function buildReminderFollowUpPolicyFromForm() {
  if (elements.reminderFollowUpActionInput.value !== "retry") {
    return null;
  }

  const maxAttempts = parseReminderPolicyInteger(elements.reminderMaxAttemptsInput.value, {
    min: 2,
    max: 10,
  });
  if (maxAttempts === null) {
    throw new Error("Choose a retry attempt budget between 2 and 10.");
  }

  const retryDelaySeconds = parseReminderPolicyInteger(elements.reminderRetryDelayInput.value, {
    min: 0,
    max: 604800,
  });
  if (retryDelaySeconds === null) {
    throw new Error("Choose a retry delay between 0 and 604800 seconds.");
  }

  return {
    on_failure: "retry",
    max_attempts: maxAttempts,
    retry_delay_seconds: retryDelaySeconds,
  };
}

function updateReminderFollowUpControls(formDisabled = false) {
  ensureReminderDefaults();
  const retryEnabled = elements.reminderFollowUpActionInput.value === "retry";
  elements.reminderMaxAttemptsInput.disabled = formDisabled || !retryEnabled;
  elements.reminderRetryDelayInput.disabled = formDisabled || !retryEnabled;

  if (formDisabled) {
    elements.reminderFollowUpMeta.textContent =
      "Retry follow-up is configured from the web control plane after sign-in and Telegram linking.";
    return;
  }

  if (!retryEnabled) {
    elements.reminderFollowUpMeta.textContent =
      "Default one-shot delivery. Telegram stays action-safe, and follow-up policy remains web/operator visible only.";
    return;
  }

  const maxAttempts =
    parseReminderPolicyInteger(elements.reminderMaxAttemptsInput.value, {
      min: 2,
      max: 10,
    }) ?? DEFAULT_REMINDER_RETRY_ATTEMPTS;
  const retryDelaySeconds =
    parseReminderPolicyInteger(elements.reminderRetryDelayInput.value, {
      min: 0,
      max: 604800,
    }) ?? DEFAULT_REMINDER_RETRY_DELAY_SECONDS;
  elements.reminderFollowUpMeta.textContent =
    `Retry on Telegram failure | ${maxAttempts} total attempt(s) | ${formatDurationSeconds(retryDelaySeconds)}. ` +
    "Total attempts include the first delivery attempt.";
}

async function saveReminder(event) {
  event.preventDefault();
  if (!hasActiveSession()) {
    setNotice("Sign in before scheduling a reminder.", "error");
    return;
  }
  if (state.telegramLink?.status !== "linked") {
    setNotice("Link Telegram before scheduling reminder delivery.", "error");
    return;
  }

  const scheduledFor = reminderInputToIso(elements.reminderAtInput.value.trim());
  if (!scheduledFor) {
    setNotice("Choose a valid reminder time.", "error");
    return;
  }
  const message = elements.reminderMessageInput.value.trim();
  if (!message) {
    setNotice("Reminder message cannot be empty.", "error");
    return;
  }
  let followUpPolicy;
  try {
    followUpPolicy = buildReminderFollowUpPolicyFromForm();
  } catch (error) {
    setNotice(error.message, "error");
    return;
  }

  try {
    setNotice("Scheduling reminder...");
    await fetchJson("/v1/reminders", {
      method: "POST",
      body: JSON.stringify({
        scheduled_for: scheduledFor,
        message,
        channel: "telegram",
        ...(followUpPolicy ? { follow_up_policy: followUpPolicy } : {}),
      }),
    });
    elements.reminderMessageInput.value = "";
    elements.reminderAtInput.value = nextReminderDateTimeValue();
    elements.reminderFollowUpActionInput.value = "none";
    elements.reminderMaxAttemptsInput.value = String(DEFAULT_REMINDER_RETRY_ATTEMPTS);
    elements.reminderRetryDelayInput.value = String(DEFAULT_REMINDER_RETRY_DELAY_SECONDS);
    await refreshReminders();
    await refreshJobs();
    renderAll();
    setNotice(
      followUpPolicy
        ? `Reminder scheduled for ${formatDate(scheduledFor)} with retry follow-up.`
        : `Reminder scheduled for ${formatDate(scheduledFor)}.`,
    );
  } catch (error) {
    setNotice(error.message || "Failed to schedule reminder.", "error");
  }
}

async function cancelReminder(reminderId) {
  try {
    setNotice("Canceling reminder...");
    await fetchJson(`/v1/reminders/${reminderId}`, {
      method: "DELETE",
    });
    await refreshReminders();
    await refreshJobs();
    renderAll();
    setNotice("Reminder canceled.");
  } catch (error) {
    setNotice(error.message || "Failed to cancel reminder.", "error");
  }
}

async function useServerCheckpoint() {
  if (!state.checkpointConflict) {
    return;
  }
  state.checkpoint = cloneJson(state.checkpointConflict.server);
  state.checkpointDraft = cloneJson(state.checkpointConflict.server);
  state.checkpointDirty = false;
  state.checkpointConflict = null;
  state.selectedMemoryIds = new Set(state.checkpoint.selected_memory_ids || []);
  await persistCheckpointDraft();
  renderCheckpointCard();
  renderMemoryList();
  setNotice("Server checkpoint restored.");
}

async function keepLocalCheckpoint() {
  if (!state.checkpointConflict) {
    return;
  }
  await saveCheckpoint(null, { force: true });
}

async function handleMemoryAction(event) {
  const button = event.target.closest("[data-memory-action]");
  if (button) {
    const memoryId = button.dataset.memoryId;
    const action = button.dataset.memoryAction;
    try {
      if (action === "archive") {
        await patchMemory(memoryId, { status: "archived" });
        state.selectedMemoryIds.delete(memoryId);
        await refreshMemory();
        renderMemoryList();
        await captureCheckpointDraft();
        setNotice("Memory archived.");
        return;
      }
      if (action === "delete") {
        const receipt = await removeMemory(memoryId);
        state.selectedMemoryIds.delete(memoryId);
        await refreshMemory();
        await refreshJobs();
        renderMemoryList();
        renderJobsCard();
        await captureCheckpointDraft();
        setNotice(`Memory deleted. Purge queued until ${formatDate(receipt.purge_after)}.`);
      }
    } catch (error) {
      setNotice(error.message || "Failed to update memory.", "error");
    }
    return;
  }

  const checkbox = event.target.closest("[data-memory-select]");
  if (!checkbox) {
    return;
  }
  const memoryId = checkbox.dataset.memorySelect;
  if (checkbox.checked) {
    state.selectedMemoryIds.add(memoryId);
  } else {
    state.selectedMemoryIds.delete(memoryId);
  }
  renderMemoryList();
  await captureCheckpointDraft();
}

async function handleReminderAction(event) {
  const button = event.target.closest("[data-reminder-action='cancel']");
  if (!button) {
    return;
  }
  await cancelReminder(button.dataset.reminderId);
}

async function handleCheckpointConflictAction(event) {
  const button = event.target.closest("[data-conflict-action]");
  if (!button) {
    return;
  }
  if (button.dataset.conflictAction === "server") {
    await useServerCheckpoint();
    return;
  }
  if (button.dataset.conflictAction === "force") {
    await keepLocalCheckpoint();
  }
}

function consumeCallbackState() {
  const url = new URL(window.location.href);
  const auth = url.searchParams.get("auth");
  if (!auth) {
    return;
  }
  if (auth === "success") {
    setNotice("Provider callback completed. Refreshing the active session.");
  } else {
    const reason = url.searchParams.get("reason") || "unknown_error";
    setNotice(`Provider callback failed: ${reason}`, "error");
  }
  url.search = "";
  window.history.replaceState({}, document.title, url.toString());
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return;
  }
  navigator.serviceWorker.register("./service-worker.js").catch(() => {
    return;
  });
}

function bindEvents() {
  elements.apiBaseInput.addEventListener("change", () => {
    state.apiBase = normalizeApiBase(elements.apiBaseInput.value) || "http://127.0.0.1:8000";
    localStorage.setItem(API_BASE_STORAGE_KEY, state.apiBase);
    renderAll();
  });
  elements.connectButton.addEventListener("click", startAuth);
  elements.refreshButton.addEventListener("click", refreshAll);
  elements.checkpointForm.addEventListener("submit", (event) => saveCheckpoint(event));
  elements.checkpointForm.addEventListener("input", () => {
    void captureCheckpointDraft();
  });
  elements.checkpointForm.addEventListener("change", () => {
    void captureCheckpointDraft();
  });
  elements.checkpointConflict.addEventListener("click", (event) => {
    void handleCheckpointConflictAction(event);
  });
  elements.telegramCard.addEventListener("click", (event) => {
    const button = event.target.closest("[data-telegram-action='start']");
    if (button) {
      void startTelegramLink();
    }
  });
  elements.reminderForm.addEventListener("submit", saveReminder);
  elements.reminderFollowUpActionInput.addEventListener("change", () => {
    updateReminderFollowUpControls(!hasActiveSession() || state.telegramLink?.status !== "linked");
  });
  elements.reminderMaxAttemptsInput.addEventListener("input", () => {
    updateReminderFollowUpControls(!hasActiveSession() || state.telegramLink?.status !== "linked");
  });
  elements.reminderRetryDelayInput.addEventListener("input", () => {
    updateReminderFollowUpControls(!hasActiveSession() || state.telegramLink?.status !== "linked");
  });
  elements.remindersCard.addEventListener("click", (event) => {
    void handleReminderAction(event);
  });
  elements.memoryForm.addEventListener("submit", saveMemory);
  elements.exportMemoryButton.addEventListener("click", exportMemory);
  elements.memoryList.addEventListener("click", (event) => {
    void handleMemoryAction(event);
  });
  elements.memoryList.addEventListener("change", (event) => {
    void handleMemoryAction(event);
  });
  elements.memoryBrokerForm.addEventListener("submit", saveMemoryBrokerScope);
  elements.brokerWorkspaceIdInput.addEventListener("change", () => {
    void handleMemoryBrokerWorkspaceChange();
  });
  elements.probeBrokerButton.addEventListener("click", () => {
    void probeMemoryBroker();
  });
}

async function bootstrap() {
  bindEvents();
  registerServiceWorker();
  await hydrateFromCache();
  consumeCallbackState();
  await refreshAll();
}

bootstrap();
