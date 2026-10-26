// webapp/packages/webui/src/services/runService.js
//
// thin client for the run registry endpoints.
// All requests inherit credentials/cookie behavior from fetchInterceptor.

import appConfig from '../config';

const BASE = (appConfig?.api?.baseUrl || '').replace(/\/$/, '');

async function jsonOrThrow(resp, action) {
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`${action} failed: ${resp.status} ${text}`);
  }
  return resp.json();
}

/** POST /agents/run-code/start — returns {runId, status}. */
export async function startRun(payload) {
  const resp = await fetch(`${BASE}/agents/run-code/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(resp, 'startRun');
}

/** GET /runs — returns {runs: [...]}.
 *
 * Pass an `agentId` to restrict to one agent's runs (server-side filter
 * via ?agent_id=). The per-agent runs screen uses this so its
 * past-runs list shows only that agent's history.
 */
export async function listRuns(agentId) {
  const qs = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : '';
  const resp = await fetch(`${BASE}/runs${qs}`);
  return jsonOrThrow(resp, 'listRuns');
}

/** GET /runs/{runId} — full record. */
export async function getRun(runId) {
  const resp = await fetch(`${BASE}/runs/${encodeURIComponent(runId)}`);
  return jsonOrThrow(resp, 'getRun');
}

/** POST /runs/{runId}/stop. Returns 202 on success. */
export async function stopRun(runId) {
  const resp = await fetch(`${BASE}/runs/${encodeURIComponent(runId)}/stop`, {
    method: 'POST',
  });
  if (resp.status === 202 || resp.ok) return true;
  const text = await resp.text().catch(() => '');
  throw new Error(`stopRun failed: ${resp.status} ${text}`);
}

/** POST /runs/{runId}/force-complete — clear a run stuck in 'running'.
 *
 * For orphaned records: a run whose owning worker died leaves a row
 * saying 'running' forever, and /stop cannot help because it flips a
 * cancel token nothing is left to observe.
 *
 * The server refuses (409) when the run produced a trace event
 * recently, on the grounds that it is probably alive and this is a
 * misclick. Pass force=true to override — the UI does that only behind
 * a second confirmation.
 *
 * Returns {runId, status, changed, detail?}. `changed: false` means the
 * run was already terminal (idempotent, not an error).
 */
export async function forceCompleteRun(runId, { force = false } = {}) {
  const resp = await fetch(
    `${BASE}/runs/${encodeURIComponent(runId)}/force-complete`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force }),
    },
  );
  if (resp.status === 409) {
    // Distinguishable so the caller can offer "clear anyway" rather
    // than surfacing a raw error string.
    const body = await resp.json().catch(() => ({}));
    const err = new Error(body.detail || 'Run appears to still be active.');
    err.code = 'RUN_LOOKS_ACTIVE';
    throw err;
  }
  return jsonOrThrow(resp, 'forceCompleteRun');
}

export default { startRun, listRuns, getRun, stopRun, forceCompleteRun };