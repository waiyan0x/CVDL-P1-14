import {AnnouncementGate, busAnnouncement} from '../core/bus-announcements.js';

export class SpeechControls {
  constructor({read, stop, status, automatic, currentDistance = () => null}) {
    this.controls = {read, stop, status, automatic};
    this.synth = window.speechSynthesis;
    this.supported = !!this.synth && typeof window.SpeechSynthesisUtterance === 'function';
    this.latest = null;
    this.active = null;
    this.gate = new AnnouncementGate();
    read.addEventListener('click', () => {
      if (!this.latest) return;
      const {data} = this.latest;
      const text = busAnnouncement(data, {distance: currentDistance()});
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
      if (automatic.checked) this.speak('Automatic bus announcements enabled.');
      else this.setStatus('Automatic announcements off.');
    });
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
    const text = busAnnouncement(data, {distance, confirmedOnly: true});
    const now = performance.now();
    if (this.gate.ready(text, now) && !this.active && this.speak(text)) this.gate.announced(text, now);
  }

  speak(text) {
    if (!this.supported || !text) return false;
    this.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = this.synth.getVoices().filter(voice => voice.localService && /^en\b/i.test(voice.lang));
    utterance.voice = voices.find(voice => /^en[-_]sg$/i.test(voice.lang)) || voices[0] || null;
    utterance.lang = utterance.voice?.lang || 'en-SG';
    utterance.rate = .95;
    this.active = utterance;
    this.setStatus('');
    utterance.onend = () => this.finish(utterance);
    utterance.onerror = () => this.finish(utterance, true);
    this.refresh();
    try {
      this.synth.speak(utterance);
      return true;
    } catch {
      this.finish(utterance, true);
      return false;
    }
  }

  finish(utterance, failed = false) {
    if (this.active !== utterance) return;
    this.active = null;
    if (failed) {
      if (this.controls.automatic) this.controls.automatic.checked = false;
      this.setStatus('Speech could not play. Try Read result aloud or check your browser’s speech settings.');
    }
    this.refresh();
  }

  cancel() {
    if (!this.active) return;
    this.active = null; // Ignore events from a cancelled or superseded utterance.
    this.synth.cancel();
    this.refresh();
  }

  reset({keepResult = false} = {}) {
    this.cancel();
    this.gate.reset();
    if (!keepResult) this.latest = null;
    this.refresh();
  }
}
