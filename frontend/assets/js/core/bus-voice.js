// Browser voice, used only when the ElevenLabs voice cannot play.
export function createBusUtterance(synth, text, language = 'en') {
  const utterance = new SpeechSynthesisUtterance(text);
  const prefix = language === 'zh' ? /^zh\b/i : /^en\b/i;
  const local = language === 'zh' ? /^zh[-_](sg|cn)$/i : /^en[-_]sg$/i;
  const voices = synth.getVoices().filter(voice => voice.localService && prefix.test(voice.lang));
  utterance.voice = voices.find(voice => local.test(voice.lang)) || voices[0] || null;
  utterance.lang = utterance.voice?.lang || (language === 'zh' ? 'zh-CN' : 'en-SG');
  utterance.rate = .95;
  return utterance;
}
