'use strict';
const $ = id => document.getElementById(id);
const labels = {easyocr:'EasyOCR baseline', tesseract:'Tesseract baseline', trocr:'Supplied fine-tuned TrOCR'};
const state = {ready:false, busy:false, running:false, generation:0, samples:[], mode:'sample', stream:null, timer:null, objectURL:null, history:[]};
const video = $('source-video');
const canvas = $('preview');
const context = canvas.getContext('2d');

function status(message, error=false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
function controls() {
  for (const id of ['analyse','replay','camera','upload','sample','backend']) $(id).disabled = !state.ready || state.busy || state.running;
  $('stop').disabled = !state.busy && !state.running;
  $('processing').hidden = !state.busy;
  $('stage').setAttribute('aria-busy', String(state.busy));
}
function stop(message='Processing stopped. Last processed frame retained.') {
  state.running = false;
  state.generation++;
  clearTimeout(state.timer);
  video.pause();
  if (state.stream) state.stream.getTracks().forEach(track => track.stop());
  state.stream = null;
  video.srcObject = null;
  controls();
  status(message);
}
function options() {
  const body = new FormData();
  body.set('detection', $('detection').value/100);
  body.set('ocr_threshold', $('ocr-threshold').value/100);
  body.set('similarity', $('similarity').value/100);
  body.set('backend', $('backend').value);
  return body;
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
async function showImage(src, generation=state.generation, detections=[]) {
  const image = new Image();
  image.src = src;
  await image.decode();
  if (generation !== state.generation) return;
  canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
  context.drawImage(image,0,0);
  $('empty').hidden = true;
  const scale = Math.max(1,canvas.width/900);
  const colours = {bus_number:'#36ca92', destination:'#64a5ff', eds:'#ffc35c'};
  for (const detection of detections) {
    const [x1,y1,x2,y2] = detection.box;
    const colour = colours[detection.label] || '#fff';
    const text = `${detection.label.replaceAll('_',' ')} · ${Math.round(detection.confidence*100)}%`;
    context.strokeStyle = colour; context.lineWidth = 2.5*scale;
    context.strokeRect(x1,y1,x2-x1,y2-y1);
    context.font = `600 ${12*scale}px -apple-system, sans-serif`;
    const textWidth = context.measureText(text).width + 12*scale;
    const labelY = Math.max(0,y1-22*scale);
    const labelX = Math.max(0,Math.min(x1,canvas.width-textWidth));
    context.fillStyle = colour; context.fillRect(labelX,labelY,textWidth,22*scale);
    context.fillStyle = '#102431'; context.fillText(text,labelX+6*scale,labelY+15*scale);
  }
}
function renderResults(data, requestMs) {
  $('latency').textContent = `${data.latency_ms} ms`;
  $('fps').textContent = `${data.processing_fps} fps`;
  $('regions').textContent = data.detections.length;
  $('roundtrip').textContent = `${Math.round(requestMs)} ms`;
  $('engine-label').textContent = labels[data.backend];
  const container = $('results'); container.replaceChildren();
  if (!data.results.length) {
    const empty = element('div',null,'result-empty');
    empty.append(element('span','—','empty-number'),element('h3','No bus information detected'),element('p','No display fields passed the detection threshold. Try a clearer image or adjust the threshold.'));
    container.append(empty);
  }
  for (const result of data.results) {
    const card = element('article',null,'recognition');
    const match = result.match;
    const number = result.fields.bus_number;
    const top = element('div',null,'bus-result');
    const rawNumber = number?.raw || '?';
    const summary = element('div');
    const accepted = match.status === 'matched';
    summary.append(element('span',accepted?'Reference endpoint matched':match.status === 'service_only'?'Service matched · endpoint unconfirmed':'Raw OCR · reference unconfirmed',`match-state ${accepted?'':'partial'}`));
    summary.append(element('h3',match.endpoint || 'Destination unconfirmed'));
    summary.append(element('p',result.message));
    top.append(element('div',match.service || (rawNumber.length<=5?rawNumber:'?'),'route-number'),summary);
    card.append(top);
    for (const [name,field] of Object.entries(result.fields)) {
      const row = element('div',null,'field-row');
      const content = element('div');
      content.append(element('h4',name==='bus_number'?'Raw service OCR':'Raw destination / road OCR'));
      content.append(element('div',field.raw || 'No text recognised','raw-text'));
      const confidence = element('div',null,'confidence');
      confidence.append(element('span',`Detection ${Math.round(field.confidence*100)}%`),element('span',`OCR score ${Math.round(field.ocr_confidence*100)}%`));
      content.append(confidence);
      const crop = element('img'); crop.src=field.crop; crop.alt=`Detected ${name.replaceAll('_',' ')} crop`;
      row.append(content,crop); card.append(row);
    }
    if (match.routes?.length) {
      const reference = element('div',null,'reference');
      reference.append(element('strong','Route reference · direction unverified'));
      for (const route of match.routes) reference.append(element('div',`${route.origin} ↔ ${route.destination || '(destination missing)'}`));
      card.append(reference);
    }
    if (match.similarity !== null) card.append(element('p',`Endpoint similarity: ${Math.round(match.similarity*100)}%${accepted?'':' · rejected'}`,'match-reason'));
    card.append(element('p',match.reason,'match-reason'));
    container.append(card);
  }
  const services = data.results.map(r=>r.match.service || r.fields.bus_number?.raw || '?').join(', ') || 'No display';
  state.history.unshift({time:new Date().toLocaleTimeString('en-SG'),services,ms:data.latency_ms,engine:labels[data.backend]});
  state.history = state.history.slice(0,20);
  $('history-count').textContent = `${state.history.length} frames`;
  $('history-list').replaceChildren(...state.history.map(entry=>{
    const row = element('div',null,'history-entry');
    row.append(element('span',`${entry.time} · Service ${entry.services}`),element('span',`${entry.ms} ms · ${entry.engine}`));
    return row;
  }));
}
async function processFrame(url, body, generation) {
  if (state.busy) return;
  state.busy=true; controls();
  status('Detecting display fields and reading text…');
  const start = performance.now();
  try {
    const response = await fetch(url,{method:'POST',body});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Unable to process this image.');
    if (generation !== state.generation) return;
    await showImage(data.image,generation,data.detections);
    renderResults(data,performance.now()-start);
    status(`${data.message} · ${labels[data.backend]}. OCR scores are heuristics, not calibrated accuracy.`);
  } catch(error) {
    if (generation === state.generation) {
      state.running=false;
      clearTimeout(state.timer);
      if (state.stream) state.stream.getTracks().forEach(track=>track.stop());
      state.stream=null; video.pause();
      status(error.message,true);
    }
  } finally { state.busy=false; controls(); }
}
async function selectSample() {
  stop('Project photo selected. Select Recognise image to run inference.');
  state.mode='sample';
  const sample=state.samples[Number($('sample').value)];
  if (!sample) return;
  $('source-label').textContent=`${sample.name} · included project dataset`;
  await showImage(sample.url);
  $('results').replaceChildren(element('div','Image selected. Run recognition to read this display.','result-empty'));
  for (const id of ['latency','fps','regions','roundtrip']) $(id).textContent='—';
}
async function captureFrame() {
  const capture=$('capture');
  const scale=Math.min(1,1280/Math.max(video.videoWidth,video.videoHeight));
  capture.width=Math.max(1,Math.round(video.videoWidth*scale));
  capture.height=Math.max(1,Math.round(video.videoHeight*scale));
  capture.getContext('2d').drawImage(video,0,0,capture.width,capture.height);
  return new Promise(resolve=>capture.toBlob(resolve,'image/jpeg',.92));
}
async function loop(generation) {
  if (!state.running || generation!==state.generation) return;
  if (state.mode==='replay') {
    const sample=state.samples[Number($('sample').value)];
    $('source-label').textContent=`Photo replay · ${sample.name} · demonstration images`;
    await processFrame(`/api/samples/${sample.id}/recognize`,options(),generation);
    if (state.running && generation===state.generation) $('sample').value=(sample.id+1)%state.samples.length;
  } else {
    if (video.ended) {stop('Video finished. Last processed frame retained.');return;}
    if (video.readyState>=2) {
      const body=options(); const blob=await captureFrame();
      if (blob && state.running && generation===state.generation) {
        body.set('file',blob,'frame.jpg');
        await processFrame('/api/recognize',body,generation);
      }
    }
  }
  if (state.running && generation===state.generation) state.timer=setTimeout(()=>loop(generation),state.mode==='replay'?1800:200);
}
function startLoop(mode) {
  state.mode=mode; state.running=true; controls();
  loop(state.generation);
}
$('sample').addEventListener('change',()=>selectSample().catch(error=>status(error.message,true)));
$('analyse').addEventListener('click',async()=>{
  if (state.mode==='image' && state.imageFile) {
    const body=options();body.set('file',state.imageFile);
    await processFrame('/api/recognize',body,state.generation);
  } else {
    const sample=state.samples[Number($('sample').value)];
    await processFrame(`/api/samples/${sample.id}/recognize`,options(),state.generation);
  }
});
$('replay').addEventListener('click',()=>{stop();startLoop('replay');});
$('stop').addEventListener('click',()=>stop());
$('camera').addEventListener('click',async()=>{
  stop(); const generation=state.generation;
  try {
    status('Requesting camera access…');
    const stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720}},audio:false});
    if (generation!==state.generation) {stream.getTracks().forEach(t=>t.stop());return;}
    state.stream=stream;video.srcObject=stream;
    await video.play();
    $('source-label').textContent='Camera · latest processed frame';
    startLoop('camera');
  } catch(error) {status(`Camera unavailable: ${error.message}. Use an uploaded image or video.`,true);controls();}
});
$('upload').addEventListener('change',async event=>{
  const file=event.target.files[0]; if (!file) return;
  stop();
  if (state.objectURL) URL.revokeObjectURL(state.objectURL);
  state.objectURL=URL.createObjectURL(file);
  $('source-label').textContent=file.name;
  try {
    if (file.type.startsWith('video/')) {
      state.mode='video';
      const loaded=new Promise((resolve,reject)=>{
        video.onloadeddata=resolve;video.onerror=()=>reject(new Error('This browser cannot play the video. Try an H.264 MP4 or WebM.'));
      });
      video.src=state.objectURL;video.load();await loaded;await video.play();
      startLoop('video');
    } else {
      state.mode='image';state.imageFile=file;
      await showImage(state.objectURL);
      const body=options();body.set('file',file);
      await processFrame('/api/recognize',body,state.generation);
    }
  } catch(error) {status(error.message,true);controls();}
  event.target.value='';
});
for (const [id,output] of [['detection','detection-value'],['ocr-threshold','ocr-value'],['similarity','similarity-value']]) {
  $(id).addEventListener('input',()=>$(output).textContent=`${$(id).value}%`);
}
$('backend').addEventListener('change',()=>{
  $('engine-label').textContent=labels[$('backend').value];
  status($('backend').value==='trocr'?'TrOCR loads on its first request; allow extra time for the first frame.':'OCR engine selected. Run recognition to compare results.');
});
window.addEventListener('pagehide',()=>stop());
async function initialise() {
  try {
    const [health,samples]=await Promise.all([fetch('/api/health').then(r=>r.json()),fetch('/api/samples').then(r=>r.json())]);
    if (!health.ready) throw new Error(health.error || 'Models are not ready.');
    state.ready=true;state.samples=samples;
    $('health').textContent='Models ready';
    $('backend').replaceChildren(...health.backends.map(backend=>{
      const option=element('option',labels[backend]);option.value=backend;return option;
    }));
    $('sample').replaceChildren(...samples.map(sample=>{
      const option=element('option',sample.name);option.value=sample.id;return option;
    }));
    controls();await selectSample();
    status(`Ready · ${health.detector} · ${health.reference_rows} reference rows. Choose an image to begin.`);
  } catch(error) {$('health').textContent='Setup needed';status(error.message,true);}
}
initialise();
