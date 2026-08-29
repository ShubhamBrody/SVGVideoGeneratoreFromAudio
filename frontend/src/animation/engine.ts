// Compiles a Scene DSL timeline into a GSAP timeline. This is the deterministic
// renderer: the same scene always animates identically. Object position, scale
// and opacity are controlled entirely here (never via React attributes) to avoid
// fighting React over the SVG `transform`.
import { gsap } from 'gsap';
import type { Scene, TimelineStep } from '../types/scene';

export interface EngineCallbacks {
  onProgress?: (progress: number) => void;
  onSubtitle?: (text: string) => void;
  onStart?: () => void;
  onComplete?: () => void;
}

const STATE_COLORS: Record<string, string> = {
  unhealthy: '#ef4444',
  healthy: '#22c55e',
  highlighted: '#38bdf8',
  normal: '#38bdf8',
  dimmed: '#64748b',
};

interface StepContext {
  objEl: (id: string) => Element | null;
  iconEl: (id: string) => Element | null;
  ringEl: (id: string) => Element | null;
  pathEl: (id: string) => SVGPathElement | null;
  trafficEl: (id: string) => SVGPathElement | null;
  lengths: Map<string, number>;
  svg: SVGSVGElement;
  cb: EngineCallbacks;
}

export function buildSceneTimeline(
  svg: SVGSVGElement,
  scene: Scene,
  cb: EngineCallbacks = {},
): gsap.core.Timeline {
  const byId = <T extends Element>(id: string) => svg.querySelector<T>(`[id="${id}"]`);
  const ctx: StepContext = {
    objEl: (id) => byId(`obj-${id}`),
    iconEl: (id) => byId(`icon-${id}`),
    ringEl: (id) => byId(`ring-${id}`),
    pathEl: (id) => byId<SVGPathElement>(`edge-path-${id}`),
    trafficEl: (id) => byId<SVGPathElement>(`edge-traffic-${id}`),
    lengths: new Map<string, number>(),
    svg,
    cb,
  };

  // --- initial state: everything hidden and positioned ---
  for (const obj of scene.objects) {
    const el = ctx.objEl(obj.id);
    if (el) {
      gsap.set(el, {
        x: obj.position.x,
        y: obj.position.y,
        scale: 0.85,
        opacity: 0,
        transformOrigin: '50% 50%',
      });
    }
    const ring = ctx.ringEl(obj.id);
    if (ring) gsap.set(ring, { opacity: 0, scale: 1, transformOrigin: '50% 50%' });
  }
  for (const edge of scene.edges) {
    const path = ctx.pathEl(edge.id);
    if (path) {
      const len = path.getTotalLength?.() ?? 300;
      ctx.lengths.set(edge.id, len);
      gsap.set(path, { strokeDasharray: len, strokeDashoffset: len, opacity: 0 });
    }
    const traffic = ctx.trafficEl(edge.id);
    if (traffic) gsap.set(traffic, { strokeDasharray: '10 14', strokeDashoffset: 0, opacity: 0 });
  }

  const tl = gsap.timeline({
    paused: true,
    onUpdate: () => cb.onProgress?.(tl.progress()),
    onStart: () => cb.onStart?.(),
    onComplete: () => cb.onComplete?.(),
  });

  let maxEnd = 0;
  for (const step of scene.timeline) {
    const at = Math.max(0, step.at);
    const dur = step.duration > 0 ? step.duration : 0.5;
    maxEnd = Math.max(maxEnd, at + dur);
    applyStep(tl, step, at, dur, ctx);
  }

  // pad the end so progress reaches 1 and the final subtitle has time to read
  tl.to({}, { duration: 0.01 }, maxEnd + 0.15);
  tl.call(() => cb.onSubtitle?.(''), undefined, maxEnd + 0.1);

  return tl;
}

function applyStep(
  tl: gsap.core.Timeline,
  step: TimelineStep,
  at: number,
  dur: number,
  ctx: StepContext,
): void {
  const target = step.target;
  const params = (step.params ?? {}) as Record<string, unknown>;

  switch (step.action) {
    case 'appear': {
      const el = ctx.objEl(target);
      if (el) tl.to(el, { opacity: 1, scale: 1, duration: dur, ease: 'back.out(1.5)' }, at);
      break;
    }
    case 'disappear': {
      const el = ctx.objEl(target);
      if (el) tl.to(el, { opacity: 0, scale: 0.9, duration: dur, ease: 'power2.in' }, at);
      break;
    }
    case 'remove': {
      const el = ctx.objEl(target);
      if (el) tl.to(el, { opacity: 0, scale: 0.5, duration: dur, ease: 'power2.in' }, at);
      const ring = ctx.ringEl(target);
      if (ring) tl.to(ring, { opacity: 0, duration: dur * 0.5 }, at);
      break;
    }
    case 'move': {
      const el = ctx.objEl(target);
      const to = params.to as { x: number; y: number } | undefined;
      if (el && to) tl.to(el, { x: to.x, y: to.y, duration: dur, ease: 'power2.inOut' }, at);
      break;
    }
    case 'highlight': {
      const ring = ctx.ringEl(target);
      const el = ctx.objEl(target);
      if (ring) {
        tl.to(ring, { opacity: 1, stroke: '#38bdf8', duration: 0.25 }, at);
        tl.to(ring, { opacity: 0, duration: 0.3 }, at + dur);
      }
      if (el) tl.to(el, { scale: 1.08, duration: dur / 2, yoyo: true, repeat: 1, ease: 'sine.inOut' }, at);
      break;
    }
    case 'pulse': {
      const ring = ctx.ringEl(target);
      if (ring) {
        tl.set(ring, { stroke: '#38bdf8' }, at);
        tl.fromTo(
          ring,
          { opacity: 0.85, scale: 1 },
          { opacity: 0, scale: 1.4, duration: Math.max(0.5, dur), repeat: 1, ease: 'power1.out' },
          at,
        );
      }
      break;
    }
    case 'change_state': {
      const state = String(params.state ?? 'highlighted');
      const color = STATE_COLORS[state] ?? '#38bdf8';
      const ring = ctx.ringEl(target);
      const el = ctx.objEl(target);
      if (state === 'normal') {
        if (ring) tl.to(ring, { opacity: 0, duration: dur }, at);
        if (el) tl.to(el, { scale: 1, duration: dur }, at);
      } else {
        if (ring) tl.to(ring, { opacity: 1, stroke: color, scale: 1, duration: 0.3 }, at);
        if (state === 'unhealthy') {
          if (ring)
            tl.fromTo(
              ring,
              { scale: 1, opacity: 0.9 },
              { scale: 1.35, opacity: 0.25, duration: 0.7, repeat: 2, ease: 'power1.out' },
              at + 0.2,
            );
          if (el) tl.to(el, { scale: 0.94, duration: 0.4, ease: 'power2.out' }, at);
        } else if (state === 'healthy') {
          if (el) tl.fromTo(el, { scale: 0.94 }, { scale: 1, duration: 0.5, ease: 'back.out(2)' }, at);
        } else if (state === 'highlighted') {
          if (el) tl.to(el, { scale: 1.06, duration: 0.3, yoyo: true, repeat: 1 }, at);
        }
      }
      break;
    }
    case 'connect': {
      const path = ctx.pathEl(target);
      if (path) {
        tl.to(path, { opacity: 1, duration: 0.12 }, at);
        tl.to(path, { strokeDashoffset: 0, duration: dur, ease: 'power1.inOut' }, at);
      }
      break;
    }
    case 'disconnect': {
      const path = ctx.pathEl(target);
      const traffic = ctx.trafficEl(target);
      const len = ctx.lengths.get(target) ?? 300;
      if (traffic) tl.to(traffic, { opacity: 0, duration: 0.2 }, at);
      if (path) {
        tl.to(path, { strokeDashoffset: len, duration: dur, ease: 'power1.in' }, at);
        tl.to(path, { opacity: 0, duration: 0.2 }, at + dur);
      }
      break;
    }
    case 'traffic': {
      const path = ctx.pathEl(target);
      const traffic = ctx.trafficEl(target);
      if (path) tl.to(path, { opacity: 1, duration: 0.1 }, at);
      if (traffic) {
        tl.set(traffic, { opacity: 1 }, at);
        const travel = 24 * Math.max(3, Math.round(dur * 3));
        tl.to(traffic, { strokeDashoffset: `-=${travel}`, duration: dur, ease: 'none' }, at);
        tl.to(traffic, { opacity: 0, duration: 0.3 }, at + dur);
      }
      break;
    }
    case 'rotate': {
      const icon = ctx.iconEl(target);
      const turns = Number((params.turns as number) ?? 1);
      const degrees = Number((params.degrees as number) ?? turns * 360);
      if (icon)
        tl.to(icon, { rotation: `+=${degrees}`, transformOrigin: '50% 50%', duration: dur, ease: 'power1.inOut' }, at);
      break;
    }
    case 'scale': {
      const icon = ctx.iconEl(target);
      const to = Number((params.to as number) ?? (params.factor as number) ?? 1.3);
      if (icon)
        tl.to(icon, { scale: to, transformOrigin: '50% 50%', duration: dur, ease: 'back.out(1.6)' }, at);
      break;
    }
    case 'emphasize': {
      const icon = ctx.iconEl(target);
      const ring = ctx.ringEl(target);
      if (icon)
        tl.to(icon, { scale: 1.18, transformOrigin: '50% 50%', duration: dur / 2, yoyo: true, repeat: 1, ease: 'sine.inOut' }, at);
      if (ring) {
        tl.set(ring, { stroke: '#38bdf8' }, at);
        tl.fromTo(ring, { opacity: 0.8, scale: 1 }, { opacity: 0, scale: 1.5, duration: Math.max(0.5, dur), ease: 'power1.out' }, at);
      }
      break;
    }
    case 'shake': {
      const icon = ctx.iconEl(target);
      if (icon)
        tl.to(icon, { keyframes: { x: [0, -7, 6, -5, 4, -2, 0] }, duration: Math.max(0.4, dur), ease: 'none' }, at);
      break;
    }
    case 'orbit': {
      const el = ctx.objEl(target);
      const around = params.around as { x: number; y: number } | undefined;
      if (el && around) {
        const startX = (gsap.getProperty(el, 'x') as number) ?? 0;
        const startY = (gsap.getProperty(el, 'y') as number) ?? 0;
        const radius = Number((params.radius as number) ?? (Math.hypot(startX - around.x, startY - around.y) || 90));
        const revs = Number((params.revolutions as number) ?? 1);
        const start = Math.atan2(startY - around.y, startX - around.x);
        const proxy = { a: start };
        tl.to(
          proxy,
          {
            a: start + Math.PI * 2 * revs,
            duration: dur,
            ease: 'none',
            onUpdate: () =>
              gsap.set(el, {
                x: around.x + radius * Math.cos(proxy.a),
                y: around.y + radius * Math.sin(proxy.a),
              }),
          },
          at,
        );
      }
      break;
    }
    case 'travel': {
      const from = ctx.objEl(String((params.from as string) ?? target));
      const to = ctx.objEl(String((params.to as string) ?? ''));
      if (from && to) {
        const fx = gsap.getProperty(from, 'x') as number;
        const fy = gsap.getProperty(from, 'y') as number;
        const tx = gsap.getProperty(to, 'x') as number;
        const ty = gsap.getProperty(to, 'y') as number;
        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        dot.setAttribute('r', '8');
        dot.setAttribute('fill', '#38bdf8');
        dot.setAttribute('filter', 'url(#glow)');
        ctx.svg.appendChild(dot);
        tl.set(dot, { x: fx, y: fy, opacity: 0 }, at);
        tl.to(dot, { opacity: 1, duration: 0.15 }, at);
        tl.to(dot, { x: tx, y: ty, duration: dur, ease: 'power1.inOut' }, at);
        tl.to(dot, { opacity: 0, duration: 0.25, onComplete: () => dot.remove() }, at + dur);
      }
      break;
    }
    case 'narrate': {
      const text = String(params.text ?? '');
      tl.call(() => ctx.cb.onSubtitle?.(text), undefined, at);
      break;
    }
    case 'label':
    case 'wait':
    default: {
      tl.to({}, { duration: dur }, at);
      break;
    }
  }
}
