export function createBusUtterance(synth, text) {
  const utterance = new SpeechSynthesisUtterance(text);
  const voices = synth.getVoices().filter(voice => voice.localService && /^en\b/i.test(voice.lang));
  utterance.voice = voices.find(voice => /^en[-_]sg$/i.test(voice.lang)) || voices[0] || null;
  utterance.lang = utterance.voice?.lang || 'en-SG';
  utterance.rate = .95;
  return utterance;
}
