// webapp/packages/webui/src/hooks/useRun.js
//
// subscribe to a run's SSE stream with replay-then-live
// semantics. Backed by GET /runs/{run_id}/stream from the run
// registry.
//
// The hook OPENS the stream on mount and CLOSES it on unmount. Closing
// does not affect the underlying run (that's the whole point of the
// registry). Reopening reconnects and replays.
//
// Auth-aware behavior (ISSUE-XXX):
//   - Pre-flight fetch to /runs/{run_id} before opening the EventSource.
//     A 401 there triggers fetchInterceptor's AuthExpiryModal via the
//     'auth:session-expired' event. EventSource doesn't participate in
//     the fetch interceptor, so this fetch is our auth entrypoint.
//   - Periodic /runs/{run_id} poll while streaming. Detects session
//     expiry mid-stream and triggers the same modal flow.
//   - Distinct 'disconnected' status separate from 'error' so the UI
//     can offer a Reconnect action.
//
// Note on runs surviving disconnects: with backend persistent-runs
// (ISSUE-YYY), losing the SSE stream no longer kills the underlying
// run. This hook's 'disconnected' status means "your live view is
// out of sync"; the run itself is still running. reconnect() re-opens
// the stream which replays events from the beginning, catching the
// UI up to whatever the run has done in the meantime.

import { useEffect, useRef, useState } from 'react';

// How often to ping /runs/{id} while streaming. The point is auth
// detection, not liveness (SSE has its own heartbeat). 30s is
// frequent enough that a session-expired user sees the modal
// quickly, sparse enough not to waste bandwidth on long runs.
const HEALTH_CHECK_INTERVAL_MS = 30000;

export default function useRun(runId) {
  const [events, setEvents] = useState([]);
  // connecting | running | success | error | stopped | disconnected | not_found | idle
  const [status, setStatus] = useState('connecting');
  const [final, setFinal] = useState(null);
  const sourceRef = useRef(null);
  const healthCheckRef = useRef(null);
  // Bumped by consumer to force a reconnect after re-auth or on
  // explicit user action. Changing this triggers the effect below.
  const [reconnectTick, setReconnectTick] = useState(0);

  useEffect(() => {
    if (!runId) {
      setStatus('idle');
      return;
    }

    let cancelled = false;
    setEvents([]);
    setFinal(null);
    setStatus('connecting');

    const doPreflightAndOpen = async () => {
      // Pre-flight auth check. fetchInterceptor handles 401 by
      // dispatching auth:session-expired, so we don't need to detect
      // it here — but we do need to bail out cleanly if it happens.
      let preflight;
      try {
        preflight = await fetch(`/runs/${encodeURIComponent(runId)}`, {
          credentials: 'include',
        });
      } catch {
        // Network error or fetch aborted. Treat as disconnected;
        // consumer can retry via reconnect().
        if (!cancelled) setStatus('disconnected');
        return;
      }
      if (cancelled) return;

      if (!preflight.ok) {
        if (preflight.status === 404) {
          // Run doesn't exist or user doesn't own it. Distinct
          // status so UI can render an appropriate not-found state
          // instead of a generic error.
          setStatus('not_found');
        } else if (preflight.status === 401 || preflight.status === 403) {
          // fetchInterceptor already dispatched the modal event.
          // Stop here and wait for the user to re-auth then trigger
          // reconnect(). Consumer should watch for the modal-close
          // event and call reconnect().
          setStatus('disconnected');
        } else {
          // 5xx or other unexpected. Reconnect might help if it's
          // a transient upstream issue.
          setStatus('error');
        }
        return;
      }

      // Auth OK. Open the actual SSE stream. Backend endpoint
      // handles replay-then-live automatically: any events already
      // in the trace get replayed, then live events continue.
      const es = new EventSource(
        `/runs/${encodeURIComponent(runId)}/stream`,
        { withCredentials: true },
      );
      sourceRef.current = es;

      es.addEventListener('run_id', () => {
        if (cancelled) return;
        setStatus((s) => (s === 'connecting' ? 'running' : s));
      });

      es.addEventListener('trace', (e) => {
        if (cancelled) return;
        try {
          const ev = JSON.parse(e.data);
          setEvents((prev) => [...prev, ev]);
        } catch {
          // Drop unparseable frames. The run continues independent
          // of UI; a bad JSON frame is a UI-side concern only.
        }
      });

      es.addEventListener('done', (e) => {
        if (cancelled) return;
        try {
          const payload = JSON.parse(e.data);
          setFinal({
            result: payload.result,
            error: payload.error,
            schemaWarnings: payload.schemaWarnings,
            opsLog: payload.opsLog,
          });
          setStatus(payload.outcome || 'success');
        } catch {
          setStatus('error');
        } finally {
          es.close();
          sourceRef.current = null;
          if (healthCheckRef.current) {
            clearInterval(healthCheckRef.current);
            healthCheckRef.current = null;
          }
        }
      });

      es.onerror = () => {
        if (cancelled) return;
        // EventSource auto-reconnects on transient errors. Only
        // act if the connection is definitively closed.
        if (es.readyState !== EventSource.CLOSED) return;

        // Distinguish auth-related close from other errors by doing
        // a fresh fetch. If 401, interceptor triggers the modal; we
        // set 'disconnected' so the UI can offer Reconnect after
        // re-auth. If auth is fine, treat as generic error.
        fetch(`/runs/${encodeURIComponent(runId)}`, { credentials: 'include' })
          .then((r) => {
            if (cancelled) return;
            if (r.status === 401 || r.status === 403) {
              setStatus('disconnected');
            } else {
              // Auth is fine but SSE died. Could be network glitch;
              // consumer can offer Reconnect. 'error' is fine here
              // — reconnect() will re-establish.
              setStatus((s) =>
                s === 'running' || s === 'connecting' ? 'error' : s
              );
            }
          })
          .catch(() => {
            if (!cancelled) setStatus('disconnected');
          });
      };

      // Periodic health check while streaming. Uses fetch so 401
      // goes through the interceptor, showing the modal even when
      // SSE thinks it's still fine (some proxies keep the SSE
      // socket alive even after backend auth fails).
      healthCheckRef.current = setInterval(async () => {
        if (cancelled) return;
        try {
          const r = await fetch(`/runs/${encodeURIComponent(runId)}`, {
            credentials: 'include',
          });
          if (r.status === 401 || r.status === 403) {
            // Interceptor already showed the modal. Close the stream
            // and mark disconnected so UI can prompt Reconnect.
            if (sourceRef.current) {
              sourceRef.current.close();
              sourceRef.current = null;
            }
            setStatus('disconnected');
          }
        } catch {
          // Transient network error — leave EventSource to retry.
          // Don't flip status; EventSource will hit onerror if
          // things are actually broken.
        }
      }, HEALTH_CHECK_INTERVAL_MS);
    };

    doPreflightAndOpen();

    return () => {
      cancelled = true;
      if (healthCheckRef.current) {
        clearInterval(healthCheckRef.current);
        healthCheckRef.current = null;
      }
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
    };
  }, [runId, reconnectTick]);

  // Consumer calls this to re-open the SSE stream after re-auth or
  // as a general "try again" affordance. Changing reconnectTick
  // triggers the useEffect to run again, closing the current stream
  // (via cleanup) and opening a fresh one (via the new effect body).
  const reconnect = () => setReconnectTick((n) => n + 1);

  return { events, status, final, reconnect };
}