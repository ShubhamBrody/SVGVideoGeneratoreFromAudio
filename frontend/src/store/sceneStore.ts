import { create } from 'zustand';
import { fetchAssets, generateScene } from '../api/client';
import type { AssetInfo, Scene } from '../types/scene';

export type Status =
  | 'idle'
  | 'recording'
  | 'transcribing'
  | 'generating'
  | 'ready'
  | 'error';

interface SceneState {
  scene: Scene | null;
  assets: Record<string, AssetInfo>;
  assetsLoaded: boolean;
  provider: string;
  status: Status;
  statusMessage: string;
  warnings: string[];

  // playback (driven by the animation engine)
  isPlaying: boolean;
  progress: number; // 0..1
  duration: number; // seconds
  subtitle: string;

  loadAssets: () => Promise<void>;
  generate: (text: string) => Promise<void>;
  applyScene: (scene: Scene, provider: string) => void;
  setStatus: (status: Status, message?: string) => void;

  setPlaying: (playing: boolean) => void;
  setProgress: (progress: number) => void;
  setDuration: (duration: number) => void;
  setSubtitle: (subtitle: string) => void;
}

export const useSceneStore = create<SceneState>((set, get) => ({
  scene: null,
  assets: {},
  assetsLoaded: false,
  provider: '',
  status: 'idle',
  statusMessage: '',
  warnings: [],

  isPlaying: false,
  progress: 0,
  duration: 0,
  subtitle: '',

  loadAssets: async () => {
    if (get().assetsLoaded) return;
    try {
      const manifest = await fetchAssets();
      const map: Record<string, AssetInfo> = {};
      for (const asset of manifest.assets) map[asset.type] = asset;
      set({ assets: map, assetsLoaded: true });
    } catch (err) {
      set({ status: 'error', statusMessage: `Failed to load assets: ${(err as Error).message}` });
    }
  },

  generate: async (text: string) => {
    set({ status: 'generating', statusMessage: 'Generating scene\u2026' });
    try {
      const res = await generateScene(text);
      get().applyScene(res.scene, res.provider);
    } catch (err) {
      set({ status: 'error', statusMessage: (err as Error).message });
    }
  },

  applyScene: (scene, provider) =>
    set({
      scene,
      provider,
      warnings: scene.warnings ?? [],
      status: 'ready',
      statusMessage: '',
      subtitle: '',
      progress: 0,
    }),

  setStatus: (status, message = '') => set({ status, statusMessage: message }),

  setPlaying: (isPlaying) => set({ isPlaying }),
  setProgress: (progress) => set({ progress }),
  setDuration: (duration) => set({ duration }),
  setSubtitle: (subtitle) => set({ subtitle }),
}));
