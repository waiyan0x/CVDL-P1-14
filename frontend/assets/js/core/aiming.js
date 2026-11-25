// Camera aiming hints for Live, derived from the detection boxes of the latest frame.
// They help a user who cannot see the screen point the camera at the bus sign.

const EDGE = .015;        // A box within 1.5% of a frame edge is treated as cut off.
const SMALL = .08;        // A sign narrower than 8% of the frame width is far away.
export const NO_SIGN_MS = 5000;

const HINTS = {
  none: 'No bus sign in view.',
  left: 'Sign cut off on the left. Turn slightly left.',
  right: 'Sign cut off on the right. Turn slightly right.',
  top: 'Sign cut off at the top. Tilt up slightly.',
  bottom: 'Sign cut off at the bottom. Tilt down slightly.',
  wide: 'Sign fills the view. Step back or zoom out.',
  small: 'Bus sign is small. The bus may still be far away.',
};

// The display's own box, or the union of its field boxes when no display box was detected.
function displayBox(result) {
  const boxes = result.screen?.box ? [result.screen.box] : Object.values(result.fields ?? {}).map(field => field?.box);
  const valid = boxes.filter(box => Array.isArray(box) && box.length === 4 && box.every(Number.isFinite));
  if (!valid.length) return null;
  return valid.reduce((u, b) => [Math.min(u[0], b[0]), Math.min(u[1], b[1]), Math.max(u[2], b[2]), Math.max(u[3], b[3])]);
}

// The nearest (largest) display box in the frame, or null when no sign was found.
export function nearestSign(data) {
  let best = null, bestArea = 0;
  for (const result of data?.results ?? []) {
    const box = displayBox(result);
    const area = box ? (box[2] - box[0]) * (box[3] - box[1]) : 0;
    if (area > bestArea) { best = box; bestArea = area; }
  }
  return best;
}

// Returns {code, side, text} or null. side places the on-screen hint next to the problem edge.
// sinceSignMs: how long no sign has been found (0 when this frame has one).
export function aimingHint(data, {sinceSignMs = 0} = {}) {
  const {width, height} = data ?? {};
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null;
  const box = nearestSign(data);
  if (!box) return sinceSignMs >= NO_SIGN_MS ? {code: 'none', side: 'center', text: HINTS.none} : null;
  const [left, top, right, bottom] = box;
  const mx = Math.max(3, width * EDGE), my = Math.max(3, height * EDGE);
  const atLeft = left <= mx, atRight = right >= width - mx;
  const hint = code => ({code, side: code === 'wide' || code === 'small' ? 'center' : code, text: HINTS[code]});
  if (atLeft && atRight) return hint('wide');
  if (atLeft) return hint('left');
  if (atRight) return hint('right');
  if (top <= my) return hint('top');
  if (bottom >= height - my) return hint('bottom');
  if ((right - left) / width < SMALL) return hint('small');
  return null;
}

// Speaks a hint only after it is seen on two frames in a row, leaves a gap after any speech,
// and repeats the same hint at most every `repeat` milliseconds.
export class HintGate {
  constructor({gap = 4000, repeat = 15000} = {}) {
    this.gap = gap;
    this.repeat = repeat;
    this.reset();
  }

  reset() {
    this.candidate = null;
    this.consecutive = 0;
    this.last = null;
    this.lastAt = -Infinity;
  }

  ready(text, now) {
    this.consecutive = text && text === this.candidate ? this.consecutive + 1 : (text ? 1 : 0);
    this.candidate = text || null;
    if (!text || this.consecutive < 2 || now - this.lastAt < this.gap) return false;
    return text !== this.last || now - this.lastAt >= this.repeat;
  }

  announced(text, now) {
    this.last = text;
    this.lastAt = now;
  }
}
