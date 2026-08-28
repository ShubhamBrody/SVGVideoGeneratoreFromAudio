import { useCallback, useLayoutEffect, useRef } from 'react';
import type { RefObject } from 'react';
import { useSceneStore } from '../store/sceneStore';
import { buildSceneTimeline } from './engine';

type SceneTimeline = ReturnType<typeof buildSceneTimeline>;

export interface SceneAnimation {
  play: () => void;
  pause: () => void;
  toggle: () => void;
  restart: () => void;
  seek: (progress: number) => void;
}

// Rebuilds the GSAP timeline whenever the scene changes and exposes transport
// controls. Playback state, progress and the current subtitle are pushed into
// the Zustand store so the UI stays in sync.
export function useSceneAnimation(svgRef: RefObject<SVGSVGElement>): SceneAnimation {
  const scene = useSceneStore((s) => s.scene);
  const setPlaying = useSceneStore((s) => s.setPlaying);
  const setProgress = useSceneStore((s) => s.setProgress);
  const setDuration = useSceneStore((s) => s.setDuration);
  const setSubtitle = useSceneStore((s) => s.setSubtitle);
  const tlRef = useRef<SceneTimeline | null>(null);

  useLayoutEffect(() => {
    tlRef.current?.kill();
    tlRef.current = null;

    const svg = svgRef.current;
    if (!svg || !scene) {
      setProgress(0);
      setDuration(0);
      return;
    }

    const tl = buildSceneTimeline(svg, scene, {
      onProgress: setProgress,
      onSubtitle: setSubtitle,
      onStart: () => setPlaying(true),
      onComplete: () => setPlaying(false),
    });
    tlRef.current = tl;
    setDuration(tl.duration());
    setProgress(0);
    tl.play(0);
    setPlaying(true);

    return () => {
      tl.kill();
      tlRef.current = null;
    };
  }, [scene, svgRef, setPlaying, setProgress, setDuration, setSubtitle]);

  const play = useCallback(() => {
    tlRef.current?.play();
    setPlaying(true);
  }, [setPlaying]);

  const pause = useCallback(() => {
    tlRef.current?.pause();
    setPlaying(false);
  }, [setPlaying]);

  const toggle = useCallback(() => {
    const tl = tlRef.current;
    if (!tl) return;
    if (tl.progress() >= 1) {
      tl.restart();
      setPlaying(true);
    } else if (tl.paused()) {
      tl.play();
      setPlaying(true);
    } else {
      tl.pause();
      setPlaying(false);
    }
  }, [setPlaying]);

  const restart = useCallback(() => {
    tlRef.current?.restart();
    setPlaying(true);
  }, [setPlaying]);

  const seek = useCallback(
    (progress: number) => {
      const tl = tlRef.current;
      if (!tl) return;
      tl.pause();
      tl.progress(Math.min(1, Math.max(0, progress)));
      setPlaying(false);
    },
    [setPlaying],
  );

  return { play, pause, toggle, restart, seek };
}
