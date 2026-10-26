// runService is a thin client over the run-registry endpoints. These
// cover the error branches, which are the ones with behaviour worth
// pinning: a 409 from force-complete has to stay distinguishable so the
// UI can offer "clear anyway" instead of surfacing a raw error string.
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import {
  startRun, listRuns, getRun, stopRun, forceCompleteRun,
} from './runService';

function mockFetch(impl) {
  globalThis.fetch = vi.fn(impl);
  return globalThis.fetch;
}

const ok = (body) => ({
  ok: true,
  status: 200,
  json: async () => body,
  text: async () => JSON.stringify(body),
});

const fail = (status, text = 'boom') => ({
  ok: false,
  status,
  json: async () => ({ detail: text }),
  text: async () => text,
});

describe('runService', () => {
  const original = globalThis.fetch;
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => { globalThis.fetch = original; });

  describe('startRun', () => {
    it('POSTs the payload and returns the parsed body', async () => {
      const f = mockFetch(async () => ok({ runId: 'r1', status: 'running' }));
      await expect(startRun({ code: 'x' })).resolves.toEqual({ runId: 'r1', status: 'running' });
      const [url, init] = f.mock.calls[0];
      expect(url).toContain('/agents/run-code/start');
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body)).toEqual({ code: 'x' });
    });

    it('throws with status and body on a non-ok response', async () => {
      mockFetch(async () => fail(500, 'kaboom'));
      await expect(startRun({})).rejects.toThrow(/startRun failed: 500 kaboom/);
    });

    it('still throws when the error body cannot be read', async () => {
      mockFetch(async () => ({
        ok: false, status: 503,
        text: async () => { throw new Error('no body'); },
      }));
      await expect(startRun({})).rejects.toThrow(/startRun failed: 503/);
    });
  });

  describe('listRuns', () => {
    it('omits the query string when no agentId is given', async () => {
      const f = mockFetch(async () => ok({ runs: [] }));
      await listRuns();
      expect(f.mock.calls[0][0]).not.toContain('agent_id');
    });

    it('filters by agentId, encoded', async () => {
      const f = mockFetch(async () => ok({ runs: [] }));
      await listRuns('a b/c');
      expect(f.mock.calls[0][0]).toContain('?agent_id=a%20b%2Fc');
    });
  });

  describe('getRun', () => {
    it('encodes the run id', async () => {
      const f = mockFetch(async () => ok({ runId: 'a/b' }));
      await getRun('a/b');
      expect(f.mock.calls[0][0]).toContain('/runs/a%2Fb');
    });

    it('throws on 404', async () => {
      mockFetch(async () => fail(404, 'missing'));
      await expect(getRun('nope')).rejects.toThrow(/getRun failed: 404/);
    });
  });

  describe('stopRun', () => {
    it('accepts 202', async () => {
      mockFetch(async () => ({ ok: false, status: 202, text: async () => '' }));
      await expect(stopRun('r1')).resolves.toBe(true);
    });

    it('accepts any other ok response', async () => {
      mockFetch(async () => ok({}));
      await expect(stopRun('r1')).resolves.toBe(true);
    });

    it('throws on a failure status', async () => {
      mockFetch(async () => fail(500, 'nope'));
      await expect(stopRun('r1')).rejects.toThrow(/stopRun failed: 500 nope/);
    });
  });

  describe('forceCompleteRun', () => {
    it('defaults force to false', async () => {
      const f = mockFetch(async () => ok({ runId: 'r1', changed: true }));
      await forceCompleteRun('r1');
      expect(JSON.parse(f.mock.calls[0][1].body)).toEqual({ force: false });
    });

    it('passes force through when asked', async () => {
      const f = mockFetch(async () => ok({ runId: 'r1', changed: true }));
      await forceCompleteRun('r1', { force: true });
      expect(JSON.parse(f.mock.calls[0][1].body)).toEqual({ force: true });
    });

    it('tags a 409 so the caller can offer "clear anyway"', async () => {
      mockFetch(async () => fail(409, 'Run appears to still be active.'));
      await expect(forceCompleteRun('r1')).rejects.toMatchObject({
        code: 'RUN_LOOKS_ACTIVE',
        message: 'Run appears to still be active.',
      });
    });

    it('falls back to a default message when the 409 body is unparseable', async () => {
      mockFetch(async () => ({
        ok: false, status: 409,
        json: async () => { throw new Error('not json'); },
      }));
      await expect(forceCompleteRun('r1')).rejects.toMatchObject({
        code: 'RUN_LOOKS_ACTIVE',
      });
    });

    it('reports changed:false without treating it as an error', async () => {
      mockFetch(async () => ok({ runId: 'r1', status: 'error', changed: false }));
      await expect(forceCompleteRun('r1')).resolves.toMatchObject({ changed: false });
    });

    it('throws on other failure statuses', async () => {
      mockFetch(async () => fail(500, 'boom'));
      await expect(forceCompleteRun('r1')).rejects.toThrow(/forceCompleteRun failed: 500/);
    });
  });
});
