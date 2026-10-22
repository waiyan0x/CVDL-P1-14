export class APIError extends Error {
  constructor(message, code = 'request_failed', status = 0) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.status = status;
  }
}

export async function request(url, options = {}) {
  let response;
  try { response = await fetch(url, options); }
  catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new APIError('The server could not be reached. Check that the application is running, then try again.', 'network');
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error;
    throw new APIError(error?.message || 'The request could not be completed. Please try again.', error?.code, response.status);
  }
  return body;
}

export function imageForm(input, options, frame) {
  const form = new FormData();
  if (input.file) form.append('file', input.file, input.file.name || 'camera-frame.jpg');
  else form.append('sample_id', input.sampleId);
  for (const [key, value] of Object.entries({...options, ...frame})) form.append(key, value);
  return form;
}

export const analyse = (input, options, frame) => request('/api/analysis', {method: 'POST', body: imageForm(input, options, frame)});
export const compare = (input, options, frame) => request('/api/comparisons', {method: 'POST', body: imageForm(input, options, frame)});
export const jsonPost = (url, body) => request(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});

let healthPromise;
export function health() {
  healthPromise ??= request('/api/health').catch(error => { healthPromise = null; throw error; });
  return healthPromise;
}

export function validateImage(file, maxBytes = 16 * 1024 * 1024) {
  if (!file || !file.size) throw new APIError('Choose a non-empty image file.', 'invalid_image');
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new APIError('Choose a JPG, PNG or WebP image.', 'unsupported_image');
  if (file.size > maxBytes) throw new APIError(`The image is too large. Choose one under ${Math.round(maxBytes / 1048576)} MB.`, 'too_large');
}
