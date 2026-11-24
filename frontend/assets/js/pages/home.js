import '../components/layout.js';

const canvas = document.getElementById('bus-stop');
const caption = document.getElementById('demo-announcement');
const context = canvas.getContext('2d');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

const curbPosition = 109;
const approachMs = 1900;
const boardingMs = 400;
const announcementMs = 2700;
const departureMs = 750;
const busInterval = approachMs + boardingMs + departureMs;
const firstFrameMs = 600;
const detectedAt = busInterval + approachMs;
const departureAt = detectedAt + announcementMs;
const loopMs = departureAt + departureMs;
const phoneLiftMs = 480;

const detectedBus = {service: '329', destination: 'Buangkok Crescent', doubleDeck: true};
const demoAnnouncement = `Bus ${detectedBus.service} to ${detectedBus.destination}.`;
const passingBus = {service: '176', doubleDeck: false};
const digits = {
  1: ['010', '110', '010', '010', '111'],
  2: ['111', '001', '111', '100', '111'],
  3: ['111', '001', '111', '001', '111'],
  6: ['111', '100', '111', '101', '111'],
  7: ['111', '001', '010', '010', '010'],
  9: ['111', '101', '111', '001', '111'],
};

function painter(target) {
  return (colour, x, y, width, height) => {
    target.fillStyle = colour;
    target.fillRect(x, y, width, height);
  };
}

function drawBlock(pixel, x, top, width, wall) {
  const ground = 116;
  pixel('#aab6ae', x + 3, top, width - 7, 3);
  pixel(wall, x, top + 3, width, ground - top - 3);
  pixel('#bdc9c2', x + width - 7, top + 3, 7, ground - top - 3);
  pixel('#e1e6df', x + 3, top + 6, 3, ground - top - 6);
  for (let y = top + 12; y < ground - 6; y += 11) {
    pixel('#e9ece7', x + 5, y + 5, width - 13, 1);
    for (let windowX = x + 7; windowX < x + width - 11; windowX += 9) {
      pixel('#a3b6ad', windowX, y, 5, 5);
      pixel('#c1cdc5', windowX + 3, y + 1, 1, 4);
    }
  }
}

function drawTree(pixel, x, base, scale) {
  const rect = (colour, left, top, width, height) => {
    pixel(colour, x + left * scale, base + top * scale, width * scale, height * scale);
  };
  rect('#79887d', -1, -9, 2, 9);
  rect('#a3b7a6', -5, -17, 10, 11);
  rect('#a3b7a6', -7, -14, 14, 6);
  rect('#809f89', -6, -11, 12, 5);
  rect('#b8c9b5', -3, -17, 5, 3);
}

function drawShelter(pixel) {
  // Covered stop, bench, route board and the yellow strip along the kerb.
  pixel('#ccd6d0', 153, 86, 99, 32);
  pixel('#dce6e0', 157, 89, 90, 24);
  pixel('#a1b3aa', 169, 87, 1, 27);
  pixel('#a1b3aa', 231, 87, 1, 27);
  pixel('#758982', 155, 85, 3, 37);
  pixel('#758982', 247, 85, 3, 37);
  pixel('#758982', 197, 85, 2, 34);
  pixel('#667a70', 159, 79, 87, 3);
  pixel('#425950', 151, 82, 102, 4);
  pixel('#adbbb1', 152, 86, 100, 2);
  pixel('#617c6f', 177, 110, 31, 3);
  pixel('#758982', 180, 113, 2, 7);
  pixel('#758982', 203, 113, 2, 7);
  pixel('#6d8879', 234, 93, 11, 15);
  pixel('#f1f4ec', 235, 95, 9, 11);
  pixel('#a4b7aa', 237, 98, 5, 1);
  pixel('#a4b7aa', 237, 101, 5, 1);

  // Lush green panel and dark green header on the bus stop pole.
  pixel('#697d75', 260, 89, 2, 35);
  pixel('#31594b', 254, 79, 14, 14);
  pixel('#a1c653', 255, 86, 12, 6);
  pixel('#f1f4ec', 258, 81, 6, 4);
  pixel('#31594b', 259, 82, 4, 1);
  pixel('#31594b', 258, 85, 1, 1);
  pixel('#31594b', 263, 85, 1, 1);
  pixel('#d9c579', 153, 124, 112, 2);
}

function drawCommuter(pixel, phoneOffset) {
  const rect = (colour, x, y, width, height) => pixel(colour, 246 + x, 125 + y, width, height);
  const skin = '#b97d5e';
  const hair = '#30373c';
  const shirt = '#7d3d49';
  const trousers = '#33434c';

  rect('#a8aaa0', -7, -1, 15, 2);
  rect(trousers, -4, -12, 4, 11);
  rect(trousers, 2, -12, 4, 11);
  rect(hair, -6, -2, 6, 2);
  rect(hair, 1, -2, 6, 2);
  rect(shirt, -5, -24, 11, 13);
  rect('#a04f5b', -4, -23, 7, 3);
  rect('#556454', 4, -23, 4, 11);
  rect(hair, -5, -36, 10, 8);
  rect(hair, -4, -37, 8, 1);
  rect(skin, -5, -32, 7, 7);
  rect(skin, -6, -30, 2, 3);
  rect(skin, -2, -26, 5, 3);
  rect(shirt, -9, -22 + phoneOffset, 6, 4);
  rect(skin, -12, -24 + phoneOffset, 5, 3);
  rect('#263538', -15, -29 + phoneOffset, 4, 8);
  rect('#acd9b2', -14, -28 + phoneOffset, 2, 5);

  // The free hand holds a white cane with a red tip.
  rect(skin, -6, -16, 2, 3);
  for (let step = 0; step < 5; step++) {
    const x = -6 - step * 2;
    const y = -14 + step * 3;
    rect('#596763', x - 1, y, 4, 4);
    rect('#f5f3ea', x, y, 2, 3);
  }
  rect('#a74637', -16, -2, 3, 2);
}

function drawStreet(target) {
  const pixel = painter(target);
  pixel('#eff2ee', 0, 0, canvas.width, canvas.height);
  pixel('#f9faf7', 169, 15, 43, 4);
  pixel('#f9faf7', 178, 12, 18, 3);
  pixel('#f9faf7', 222, 23, 34, 3);
  pixel('#dce5dd', 0, 80, canvas.width, 41);
  drawBlock(pixel, 9, 37, 49, '#d6ded7');
  drawBlock(pixel, 71, 22, 64, '#d0dbd4');
  drawBlock(pixel, 132, 50, 62, '#dee4dc');
  drawBlock(pixel, 214, 32, 55, '#d2ded7');
  drawTree(pixel, 9, 123, 2);
  drawTree(pixel, 65, 119, 2);
  drawTree(pixel, 142, 124, 2);
  drawTree(pixel, 278, 122, 2);

  pixel('#dce1d9', 0, 119, canvas.width, 9);
  pixel('#b5c0b8', 0, 126, canvas.width, 2);
  pixel('#879390', 0, 128, canvas.width, 41);
  pixel('#99a6a1', 0, 129, canvas.width, 2);
  pixel('#667775', 0, 168, canvas.width, 2);
  pixel('#b6c4ba', 0, 170, canvas.width, 6);
  for (let x = 12; x < canvas.width; x += 46) pixel('#dce2db', x, 159, 23, 2);
  drawShelter(pixel);
}

function wheel(pixel, x) {
  pixel('#283434', x + 2, -16, 10, 16);
  pixel('#283434', x, -14, 14, 12);
  pixel('#64736d', x + 4, -12, 6, 7);
  pixel('#a3ada4', x + 6, -10, 2, 3);
}

function drawBus(target, x, {service, doubleDeck}) {
  const pixel = painter(target);
  const roof = doubleDeck ? -61 : -45;
  target.save();
  target.translate(x, 151);
  pixel('#677875', 1, -3, 112, 3);

  // The solid low-floor silhouette, window band and amber destination display.
  pixel('#34463b', 2, roof, 104, 1);
  pixel('#34463b', 0, roof + 2, 112, -roof - 9);
  pixel('#34463b', 3, roof + 1, 105, -roof - 6);
  pixel('#8abe3e', 2, roof + 3, 108, -roof - 11);
  pixel('#abd15b', 5, roof + 1, 100, 2);
  pixel('#6c9a37', 4, -13, 101, 5);
  pixel('#b1d16c', 5, -24, 101, 2);
  pixel('#2c3c3b', 5, -42, 103, 17);
  pixel('#4f6a66', 8, -38, 79, 10);
  pixel('#6c8880', 8, -38, 79, 2);
  for (const divider of [22, 38, 54, 70, 84]) pixel('#2c3c3b', divider, -39, 2, 12);
  if (doubleDeck) {
    pixel('#2c3c3b', 5, -56, 103, 12);
    pixel('#57716d', 8, -54, 97, 8);
    pixel('#779087', 8, -54, 97, 1);
    for (const divider of [22, 38, 54, 70, 84, 94]) pixel('#2c3c3b', divider, -55, 2, 10);
  }

  pixel('#3c5656', 92, -33, 15, 9);
  pixel('#86a19c', 93, -32, 11, 2);
  pixel('#25312d', 91, -41, 16, 7);
  Array.from(service).forEach((digit, column) => {
    digits[digit].forEach((row, rowIndex) => {
      Array.from(row).forEach((dot, cell) => {
        if (dot === '1') pixel('#ffcb70', 94 + column * 4 + cell, -40 + rowIndex, 1, 1);
      });
    });
  });

  pixel('#eef4dc', 34, -21, 15, 2);
  pixel('#eef4dc', 36, -18, 11, 1);
  pixel('#749d42', 4, -11, 10, 2);
  pixel('#d97c6d', 2, -18, 2, 5);
  pixel('#fff0bc', 105, -18, 5, 3);
  pixel('#768781', 99, -11, 11, 2);
  pixel('#3a5148', 108, -33, 6, 2);
  pixel('#3a5148', 113, -34, 2, 5);
  wheel(pixel, 16);
  wheel(pixel, 80);
  target.restore();
}

function markDetectedDisplay() {
  const pixel = painter(context);
  const left = curbPosition + 88;
  const top = 108;
  const right = left + 22;
  const bottom = top + 11;
  for (const y of [top, bottom]) {
    pixel('#f8faf4', left, y, 5, 1);
    pixel('#f8faf4', right - 4, y, 5, 1);
  }
  for (const x of [left, right]) {
    pixel('#f8faf4', x, top, 1, 4);
    pixel('#f8faf4', x, bottom - 3, 1, 4);
  }
}

function animateArrival() {
  const street = document.createElement('canvas');
  street.width = canvas.width;
  street.height = canvas.height;
  drawStreet(street.getContext('2d'));
  const pixel = painter(context);

  let lastPosition;
  let lastBus;
  let lastPhoneOffset;
  let lastAnnouncement = false;

  function draw(time) {
    const bus = time < busInterval ? passingBus : detectedBus;
    const phase = time < busInterval ? time : time - busInterval;
    const dwellMs = bus === detectedBus ? announcementMs : boardingMs;
    const announcing = time >= detectedAt && time < departureAt;
    let x = curbPosition;
    if (phase < approachMs) {
      x -= (curbPosition + 116) * (1 - phase / approachMs) ** 3;
    } else if (phase > approachMs + dwellMs) {
      const progress = (phase - approachMs - dwellMs) / departureMs;
      x += (canvas.width + 1 - curbPosition) * progress ** 2;
    }
    x = Math.round(x);
    const timeOutsideAnnouncement = Math.max(0, detectedAt - time, time - departureAt);
    const phoneOffset = Math.round(7 * Math.min(1, timeOutsideAnnouncement / phoneLiftMs));
    if (x === lastPosition && bus === lastBus && phoneOffset === lastPhoneOffset && announcing === lastAnnouncement) return;
    context.drawImage(street, 0, 0);
    drawCommuter(pixel, phoneOffset);
    drawBus(context, x, bus);
    if (announcing) markDetectedDisplay();
    if (announcing !== lastAnnouncement) caption.hidden = !announcing;
    lastPosition = x;
    lastBus = bus;
    lastPhoneOffset = phoneOffset;
    lastAnnouncement = announcing;
  }

  let frame = null;
  let startedAt;
  function tick(now) {
    draw((firstFrameMs + now - startedAt) % loopMs);
    frame = requestAnimationFrame(tick);
  }

  function applyMotionPreference() {
    if (frame !== null) cancelAnimationFrame(frame);
    if (reducedMotion.matches) {
      frame = null;
      draw(detectedAt);
      return;
    }
    startedAt = performance.now();
    draw(firstFrameMs);
    frame = requestAnimationFrame(tick);
  }

  reducedMotion.addEventListener('change', applyMotionPreference);
  applyMotionPreference();
}

document.getElementById('demo-announcement-text').textContent = demoAnnouncement;
if (context) animateArrival();
else caption.hidden = false;
