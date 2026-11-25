import {AnnouncementGate, busAnnouncement, localPhrase} from '../core/bus-announcements.js';
import {createBusUtterance} from '../core/bus-voice.js';
import {HintGate} from '../core/aiming.js';

// Speech uses the project's ElevenLabs voices (English or Chinese, POST /api/speech/tts) and falls back to the
// browser's voice when ElevenLabs cannot be reached.
const LANGUAGE_KEY = 'eds-voice-language';
const CLIP_CACHE = 40;
// 10 ms of silence, played on a click so the browser lets later announcements play without one.
const SILENCE = 'data:audio/wav;base64,UklGRnQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YVAAAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==';

function storedLanguage() {
  try { return localStorage.getItem(LANGUAGE_KEY) === 'zh' ? 'zh' : 'en'; } catch { return 'en'; }
}

function storeLanguage(language) {
  try { localStorage.setItem(LANGUAGE_KEY, language); } catch { /* Remembering the choice is optional. */ }
}

export class SpeechControls {
  constructor({read, stop, status, automatic, language, currentDistance = () => null}) {
    this.controls = {read, stop, status, automatic};
    this.synth = window.speechSynthesis ?? null;
    this.browserVoice = !!this.synth && typeof window.SpeechSynthesisUtterance === 'function';
    this.audio = typeof window.Audio === 'function' ? new Audio() : null;
    this.supported = !!this.audio || this.browserVoice;
    this.clips = new Map();
    this.unlocked = false;
    this.language = storedLanguage();
    this.latest = null;
    this.active = null;
    this.gate = new AnnouncementGate();
    this.hints = new HintGate();
    read.addEventListener('click', () => {
      if (!this.latest) return;
      this.unlock();
      const {data} = this.latest;
      const text = busAnnouncement(data, {distance: currentDistance(), language: this.language});
      this.speak(text || (data.status === 'no_eds'
        ? 'No bus display detected.' : 'Could not read the bus display.'));
    });
    stop.addEventListener('click', () => {
      if (automatic) automatic.checked = false;
      this.reset({keepResult: true});
      this.setStatus('Speech stopped.');
    });
    automatic?.addEventListener('change', () => {
      this.reset({keepResult: true});
      if (automatic.checked) {
        this.unlock();
        this.speak('Automatic bus announcements enabled.');
      } else this.setStatus('Automatic announcements off.');
    });
    for (const input of language?.querySelectorAll('input[type="radio"]') ?? []) {
      input.checked = input.value === this.language;
      input.addEventListener('change', () => {
        if (!input.checked) return;
        this.language = input.value === 'zh' ? 'zh' : 'en';
        storeLanguage(this.language);
        this.unlock();
        this.reset({keepResult: true});
      });
    }
    if (automatic) automatic.disabled = !this.supported;
    if (!this.supported) this.setStatus('Speech is unavailable in this browser.');
    this.refresh();
  }

  setStatus(text) {
    if (this.controls.status.textContent !== text) this.controls.status.textContent = text;
  }

  refresh() {
    this.controls.read.disabled = !this.supported || !this.latest;
    this.controls.stop.disabled = !this.active;
  }

  update(data, distance = null, {announce = false} = {}) {
    this.latest = {data};
    this.refresh();
    if (!announce || !this.controls.automatic?.checked) return;
    const text = busAnnouncement(data, {distance, confirmedOnly: true, language: this.language});
    const now = performance.now();
    if (this.gate.ready(text, now) && !this.active && this.speak(text)) this.gate.announced(text, now);
  }

  // Aiming hints are spoken only with automatic announcements on, never over other speech,
  // and not within 3 s of a bus announcement.
  hint(text) {
    const now = performance.now();
    const ready = this.hints.ready(text, now);
    if (!ready || !this.controls.automatic?.checked || this.active || now - this.gate.lastAt < 3000) return;
    if (this.speak(text)) this.hints.announced(text, now);
  }

  // Browsers only allow sound that follows a click; playing silence on one keeps the audio element allowed.
  unlock() {
    if (this.unlocked || !this.audio) return;
    this.unlocked = true;
    this.audio.src = SILENCE;
    this.audio.play().catch(() => { this.unlocked = false; });
  }

  // Starts speaking and returns true; the audio itself arrives asynchronously.
  speak(text) {
    if (!this.supported || !text) return false;
    this.cancel();
    const job = {text: localPhrase(text, this.language), language: this.language, controller: new AbortController()};
    this.active = job;
    this.setStatus('');
    this.refresh();
    if (this.audio) this.play(job);
    else this.fallback(job);
    return true;
  }

  async play(job) {
    try {
      const url = await this.clip(job);
      if (this.active !== job) return;
      this.audio.onended = () => this.finish(job);
      this.audio.onerror = () => this.fallback(job);
      this.audio.src = url;
      await this.audio.play();
    } catch (error) {
      if (this.active === job && error?.name !== 'AbortError') this.fallback(job);
    }
  }

  async clip({text, language, controller}) {
    const key = `${language}\n${text}`;
    if (this.clips.has(key)) return this.clips.get(key);
    const response = await fetch('/api/speech/tts', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, language}), signal: controller.signal,
    });
    if (!response.ok) throw new Error(`Text-to-speech failed (${response.status})`);
    const url = URL.createObjectURL(await response.blob());
    this.clips.set(key, url);
    if (this.clips.size > CLIP_CACHE) {
      const [oldest, oldUrl] = this.clips.entries().next().value;
      this.clips.delete(oldest);
      URL.revokeObjectURL(oldUrl);
    }
    return url;
  }

  fallback(job) {
    if (this.active !== job || job.utterance) return;
    if (!this.browserVoice) {
      this.finish(job, true);
      return;
    }
    const utterance = createBusUtterance(this.synth, job.text, job.language);
    job.utterance = utterance;
    utterance.onend = () => this.finish(job);
    utterance.onerror = () => this.finish(job, true);
    this.setStatus('ElevenLabs voice unavailable. Using the browser voice.');
    try {
      this.synth.speak(utterance);
    } catch {
      this.finish(job, true);
    }
  }

  finish(job, failed = false) {
    if (this.active !== job) return;
    this.active = null;
    if (failed) {
      if (this.controls.automatic) this.controls.automatic.checked = false;
      this.setStatus('Speech could not play. Try Read result aloud or check your browser’s speech settings.');
    }
    this.refresh();
  }

  cancel() {
    const job = this.active;
    if (!job) return;
    this.active = null; // Ignore events from a cancelled or superseded announcement.
    job.controller.abort();
    if (this.audio) {
      this.audio.onended = this.audio.onerror = null;
      this.audio.pause();
    }
    if (job.utterance) this.synth.cancel();
    this.refresh();
  }

  reset({keepResult = false} = {}) {
    this.cancel();
    this.gate.reset();
    this.hints.reset();
    if (!keepResult) this.latest = null;
    this.refresh();
  }
}
