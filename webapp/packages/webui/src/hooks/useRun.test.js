// useRun subscribes via EventSource and surfaces events + status.
//
// NOTE ON TIMING: useRun does a pre-flight fetch to /runs/{id} before it
// opens the EventSource — that fetch is the auth entrypoint, because
// EventSource does not participate in fetchInterceptor and so cannot
// surface a 401. The stream is therefore created ASYNCHRONOUSLY, one
// microtask after mount.
//
// That means `FakeEventSource.instances[0]` is undefined immediately after
// renderHook(). Every assertion about the stream has to wait for the
// preflight to resolve. The earlier version of this file read instances[0]
// synchronously, which worked against the pre-auth hook and fails against
// this one with "Cannot read properties of undefined".
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import useRun from './useRun';

class FakeEventSource {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.readyState = 0;
    this.listeners = {};
    this.onerror = null;
    FakeEventSource.instances.push(this);
  }
  addEventListener(type, fn) {
    this.listeners[type] = (this.listeners[type] || []).concat(fn);
  }
  _emit(type, data) {
    (this.listeners[type] || []).forEach((fn) => fn({ data: JSON.stringify(data) }));
  }
  close() { this.readyState = 2; }
}

/** Wait for the preflight to resolve and the stream to be opened. */
async function openedStream() {
  await waitFor(() => expect(FakeEventSource.instances.length).toBeGreaterThan(0));
  return FakeEventSource.instances[0];
}

describe('useRun', () => {
  let originalES;
  let originalFetch;

  beforeEach(() => {
    originalES = globalThis.EventSource;
    originalFetch = globalThis.fetch;
    globalThis.EventSource = FakeEventSource;
    FakeEventSource.instances = [];
    // jsdom needs the CLOSED constant on the class
    globalThis.EventSource.CLOSED = 2;
    // The hook pre-flights GET /runs/{id} for auth, then polls it every 30s.
    // Without this mock the preflight rejects, the hook sets 'disconnected',
    // and no EventSource is ever constructed.
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }),
    );
  });

  afterEach(() => {
    globalThis.EventSource = originalES;
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('returns idle when runId is falsy', () => {
    const { result } = renderHook(() => useRun(null));
    expect(result.current.status).toBe('idle');
  });

  it('opens an EventSource for the runId and transitions to running on run_id event', async () => {
    const { result } = renderHook(() => useRun('r-1'));
    const es = await openedStream();
    expect(es.url).toContain('/runs/r-1/stream');

    act(() => es._emit('run_id', { runId: 'r-1' }));
    await waitFor(() => expect(result.current.status).toBe('running'));
  });

  it('accumulates trace events', async () => {
    const { result } = renderHook(() => useRun('r-1'));
    const es = await openedStream();

    act(() => es._emit('trace', { type: 'agent_start', ts: 1 }));
    act(() => es._emit('trace', { type: 'agent_end', ts: 2 }));

    await waitFor(() => expect(result.current.events).toHaveLength(2));
    expect(result.current.events[0].type).toBe('agent_start');
  });

  it('captures final payload and status on done', async () => {
    const { result } = renderHook(() => useRun('r-1'));
    const es = await openedStream();

    act(() => es._emit('done', {
      outcome: 'success',
      result: { ok: true },
      error: null,
      schemaWarnings: [],
      opsLog: [],
    }));

    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.final.result).toEqual({ ok: true });
    // done handler closes the stream
    expect(es.readyState).toBe(2);
  });

  it('closes the source on unmount', async () => {
    const { unmount } = renderHook(() => useRun('r-1'));
    const es = await openedStream();
    unmount();
    expect(es.readyState).toBe(2);
  });

  // --- behaviors the pre-auth hook did not have -------------------------

  it('reports not_found when the run does not exist', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) }),
    );
    const { result } = renderHook(() => useRun('missing'));
    await waitFor(() => expect(result.current.status).toBe('not_found'));
    // A 404 must NOT open a stream — the run is not ours to watch.
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it('reports disconnected (not error) when the session has expired', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) }),
    );
    const { result } = renderHook(() => useRun('r-1'));
    // 'disconnected' is deliberately distinct from 'error' so the UI can
    // offer Reconnect rather than reporting a failure.
    await waitFor(() => expect(result.current.status).toBe('disconnected'));
  });

  it('exposes reconnect() which re-opens the stream', async () => {
    const { result } = renderHook(() => useRun('r-1'));
    await openedStream();
    expect(FakeEventSource.instances).toHaveLength(1);

    act(() => result.current.reconnect());

    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(2));
    expect(FakeEventSource.instances[1].url).toContain('/runs/r-1/stream');
  });
});