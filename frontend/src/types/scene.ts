// TypeScript mirror of the backend Scene DSL (see backend/app/models/scene.py).

export type ObjectState = 'normal' | 'healthy' | 'unhealthy' | 'highlighted' | 'dimmed';

export type EdgeStyle = 'solid' | 'dashed' | 'traffic' | 'data' | 'control' | 'dependency';

export type ActionType =
  | 'appear'
  | 'disappear'
  | 'remove'
  | 'move'
  | 'highlight'
  | 'change_state'
  | 'connect'
  | 'disconnect'
  | 'traffic'
  | 'pulse'
  | 'rotate'
  | 'scale'
  | 'orbit'
  | 'travel'
  | 'emphasize'
  | 'shake'
  | 'camera'
  | 'label'
  | 'narrate'
  | 'wait';

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface SceneObject {
  id: string;
  type: string;
  label: string;
  position: Position;
  size?: Size;
  state: ObjectState;
  meta?: Record<string, unknown>;
}

export interface SceneEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  style: EdgeStyle;
}

export interface TimelineStep {
  id?: string;
  action: ActionType;
  target: string;
  at: number;
  duration: number;
  params?: Record<string, unknown>;
}

export interface Canvas {
  width: number;
  height: number;
  background: string;
}

export interface Scene {
  id: string;
  title: string;
  canvas: Canvas;
  objects: SceneObject[];
  edges: SceneEdge[];
  timeline: TimelineStep[];
  narration: string;
  warnings: string[];
}

export interface AssetInfo {
  type: string;
  label: string;
  category: string;
  keywords: string[];
  view_box: string;
  svg: string;
}

export interface AssetManifest {
  assets: AssetInfo[];
  categories: string[];
}

export interface GenerateResponse {
  scene: Scene;
  provider: string;
  warnings: string[];
}

export interface TranscriptionResponse {
  text: string;
  duration?: number | null;
  language?: string | null;
}
