/** A generation invalidates stale responses; waiting never captures an old frame. */
export class FrameSession {
  constructor() { this.generation = 0; this.inflight = null; this.reset(); }

  reset() {
    this.generation += 1;
    this.id = globalThis.crypto?.randomUUID?.() || `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    this.frameId = 0;
    return this.generation;
  }

  current(generation) { return generation === this.generation; }

  metadata(source, timestamp = 0) {
    return {session_id: this.id, frame_id: this.frameId++, source,
      source_timestamp_ms: Math.max(0, Math.round(timestamp)), captured_at: new Date().toISOString()};
  }

  async run(generation, task) {
    // Only the latest source selection continues once an outstanding request ends.
    while (this.inflight) await this.inflight.catch(() => {});
    if (!this.current(generation)) return null;
    const pending = Promise.resolve().then(task);
    this.inflight = pending;
    try {
      const result = await pending;
      return this.current(generation) ? result : null;
    } catch (error) {
      if (!this.current(generation)) return null;
      throw error;
    } finally {
      if (this.inflight === pending) this.inflight = null;
    }
  }
}

export class SamplingLoop {
  constructor(task, interval) { this.task = task; this.interval = interval; this.timer = null; this.active = false; this.generation = 0; }
  start() { this.stop(); this.active = true; this.tick(this.generation); }
  stop() { this.active = false; this.generation += 1; clearTimeout(this.timer); }
  async tick(generation) {
    const started = performance.now();
    await this.task();
    if (!this.active || generation !== this.generation) return;
    // Skip missed intervals: never enqueue frames that have already passed.
    this.timer = setTimeout(() => this.tick(generation), Math.max(0, this.interval() - (performance.now() - started)));
  }
}
