// REST + WebSocket client. All URLs are relative so the Vite dev proxy
// (see vite.config.ts) forwards them to the FastAPI backend on port 8000.
import type {
  AssetManifest,
  GenerateResponse,
  Scene,
  TranscriptionResponse,
} from '../types/scene';

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function fetchAssets(): Promise<AssetManifest> {
  return fetch('/api/assets').then((r) => asJson<AssetManifest>(r));
}

export function generateScene(text: string): Promise<GenerateResponse> {
  return fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).then((r) => asJson<GenerateResponse>(r));
}

export function transcribeAudio(
  blob: Blob,
  filename = 'audio.webm',
): Promise<TranscriptionResponse> {
  const form = new FormData();
  form.append('file', blob, filename);
  return fetch('/api/transcribe', { method: 'POST', body: form }).then((r) =>
    asJson<TranscriptionResponse>(r),
  );
}

export interface SceneSocketHandlers {
  onStatus?: (message: string) => void;
  onScene?: (scene: Scene, provider: string) => void;
  onError?: (message: string) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

/** Thin wrapper around the /ws endpoint for real-time scene generation. */
export class SceneSocket {
  private ws: WebSocket | null = null;

  constructor(private handlers: SceneSocketHandlers = {}) {}

  connect(): void {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${scheme}://${window.location.host}/ws`;
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => this.handlers.onOpen?.();
    ws.onclose = () => this.handlers.onClose?.();
    ws.onerror = () => this.handlers.onError?.('WebSocket connection error.');
    ws.onmessage = (event) => {
      let msg: { type: string; message?: string; scene?: Scene; provider?: string };
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      if (msg.type === 'status') this.handlers.onStatus?.(msg.message ?? '');
      else if (msg.type === 'error') this.handlers.onError?.(msg.message ?? 'Unknown error');
      else if (msg.type === 'scene' && msg.scene)
        this.handlers.onScene?.(msg.scene, msg.provider ?? 'unknown');
    };
  }

  get isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  send(text: string): void {
    if (this.isOpen) this.ws?.send(JSON.stringify({ text }));
  }

  close(): void {
    this.ws?.close();
    this.ws = null;
  }
}
