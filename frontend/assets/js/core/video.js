import {APIError, jsonPost, request} from './api.js';

/** Uploaded video is decoded on the server, independent of browser codecs. */
export class UploadedVideo {
  constructor() { this.media = null; this.generation = 0; }

  async upload(file, maxBytes = 200 * 1048576) {
    if (!file || !file.size) throw new APIError('Choose a non-empty video file.', 'invalid_video');
    if (file.size > maxBytes) throw new APIError(`The video is too large. Choose one under ${Math.round(maxBytes / 1048576)} MB.`, 'too_large');
    const generation = ++this.generation;
    const body = new FormData();
    body.append('file', file);
    const media = await request('/api/videos', {method: 'POST', body});
    if (generation !== this.generation) { this.release(media); return null; }
    await this.release(this.media);
    this.media = media;
    return media;
  }

  frame(timestamp, options, metadata) {
    if (!this.media) throw new APIError('Upload a video before starting.', 'missing_video');
    return jsonPost(`/api/videos/${encodeURIComponent(this.media.video_id)}/frames`, {...options, ...metadata, timestamp_ms: Math.round(timestamp)});
  }

  async release(media, {keepalive = false} = {}) {
    if (!media) return;
    await fetch(`/api/videos/${encodeURIComponent(media.video_id)}`, {method: 'DELETE', keepalive}).catch(() => {});
  }

  clear({keepalive = false} = {}) {
    this.generation += 1;
    const media = this.media;
    this.media = null;
    return this.release(media, {keepalive});
  }
}
