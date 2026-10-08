// Run with Playwright installed and this demo's server running. Uses isolated Chrome.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const root = path.resolve(__dirname, '..');
  const output = path.join(root, '.runtime');
  fs.mkdirSync(output, {recursive:true});
  const browser = await chromium.launch({channel:'chrome', headless:true,
    args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1000}, permissions:['camera']});
    const page = await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
    await page.goto('http://127.0.0.1:8000');
    await page.waitForFunction(()=>document.getElementById('health').textContent==='Models ready');
    await page.getByRole('button',{name:'Recognise image',exact:true}).click();
    await page.waitForFunction(()=>parseInt(document.getElementById('history-count').textContent)===1);
    assert.match(await page.locator('#results').innerText(), /Tampines Bus Interchange/);
    await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
    for(const width of [320,768,1024,1440]) {
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth), false, `Overflow at ${width}px`);
    }
    await page.setViewportSize({width:320,height:950});
    await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('#upload').setInputFiles(path.join(root,'data/images/test/0c7ddfa8-27d65774-133.jpg'));
    await page.waitForFunction(()=>document.getElementById('history-count').textContent==='2 frames');
    assert.match(await page.locator('#results').innerText(), /133/);
    await page.getByRole('button',{name:'Replay photos',exact:true}).click();
    await page.waitForFunction(()=>parseInt(document.getElementById('history-count').textContent)>=4);
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    await page.waitForFunction(()=>!document.getElementById('analyse').disabled);

    // Generate a labelled test fixture from a project still; this is not bus footage.
    const fixture = await page.evaluate(async()=>{
      const image=new Image(); image.src='/api/samples/0/image';await image.decode();
      const canvas=document.createElement('canvas');canvas.width=960;canvas.height=720;
      const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,960,720);
      const stream=canvas.captureStream(10);
      const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8'});
      const chunks=[];
      recorder.ondataavailable=event=>chunks.push(event.data);
      const completed=new Promise(resolve=>recorder.onstop=resolve);
      recorder.start();
      const timer=setInterval(()=>{ctx.drawImage(image,0,0,960,720);},100);
      await new Promise(resolve=>setTimeout(resolve,3500));
      recorder.stop();clearInterval(timer);await completed;stream.getTracks().forEach(t=>t.stop());
      return Array.from(new Uint8Array(await new Blob(chunks,{type:'video/webm'}).arrayBuffer()));
    });
    const videoPath=path.join(output,'fixture-photo-video.webm');
    fs.writeFileSync(videoPath,Buffer.from(fixture));
    const before=await page.locator('#history-count').innerText();
    await page.locator('#upload').setInputFiles(videoPath);
    await page.waitForFunction(old=>document.getElementById('history-count').textContent!==old,before);
    await page.waitForFunction(()=>document.getElementById('status').textContent.startsWith('Video finished'),null,{timeout:20000});
    console.log('Video upload/playback/frame recognition passed.');

    const cameraBefore=await page.locator('#history-count').innerText();
    await page.getByRole('button',{name:'Use camera',exact:true}).click();
    await page.waitForFunction(old=>document.getElementById('history-count').textContent!==old,cameraBefore);
    await page.getByRole('button',{name:'Stop',exact:true}).click();
    await page.waitForFunction(()=>!document.getElementById('analyse').disabled);
    assert.equal(await page.evaluate(()=>document.getElementById('source-video').srcObject),null);
    console.log('Simulated camera processing and stop passed.');
    assert.deepEqual(errors,[],'Browser console/page errors');
    console.log('Image upload, recognition, replay, mobile widths, video, simulated camera: PASS');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
