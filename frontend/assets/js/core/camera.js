import {APIError} from './api.js';

export class Camera {
  constructor(video) { this.video = video; this.stream = null; this.generation = 0; }

  async open() {
    this.close();
    const generation = this.generation;
    if (!navigator.mediaDevices?.getUserMedia) throw new APIError('Camera access is unavailable. Use a supported browser on localhost or HTTPS, or upload an image or video.', 'camera_unsupported');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: false, video: {facingMode: {ideal: 'environment'}, width: {ideal: 1280}}});
      if (generation !== this.generation) { stream.getTracks().forEach(track => track.stop()); return false; }
      this.stream = stream;
      this.video.srcObject = stream;
      await this.video.play();
      return true;
    } catch (error) {
      if (generation !== this.generation) return false;
      this.close();
      const messages = {
        NotAllowedError: 'Camera permission was denied. Allow camera access in your browser settings, then try again.',
        NotFoundError: 'No camera is available on this device. Connect a camera or upload a file.',
        NotReadableError: 'The camera could not be opened. Close other apps using it, then try again.',
        OverconstrainedError: 'This camera does not support the requested video settings. Try another camera or upload a file.',
      };
      throw new APIError(messages[error.name] || 'The camera could not be started. Check its connection and browser permission, then try again.', 'camera_failed');
    }
  }

  close() {
    this.generation += 1;
    this.stream?.getTracks().forEach(track => track.stop());
    this.stream = null;
    this.video.srcObject = null;
  }

  async capture() {
    if (!this.stream?.getVideoTracks().some(track => track.readyState === 'live') || this.video.readyState < 2 || !this.video.videoWidth) throw new APIError('The camera is not ready or has disconnected. Restart it and wait for its preview.', 'camera_not_ready');
    const scale = Math.min(1, 1280 / Math.max(this.video.videoWidth, this.video.videoHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(this.video.videoWidth * scale);
    canvas.height = Math.round(this.video.videoHeight * scale);
    canvas.getContext('2d').drawImage(this.video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new APIError('The camera frame could not be captured. Please try again.')), 'image/jpeg', .9));
  }
}
