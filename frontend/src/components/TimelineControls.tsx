import { useSceneStore } from '../store/sceneStore';
import type { SceneAnimation } from '../animation/useSceneAnimation';
import { PlayIcon, PauseIcon, RestartIcon } from './icons';
import WarningsBadge from './WarningsBadge';

interface Props {
  controls: SceneAnimation;
}

export default function TimelineControls({ controls }: Props) {
  const scene = useSceneStore((s) => s.scene);
  const isPlaying = useSceneStore((s) => s.isPlaying);
  const progress = useSceneStore((s) => s.progress);
  const duration = useSceneStore((s) => s.duration);

  if (!scene) return null;

  const onSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    controls.seek((e.clientX - rect.left) / rect.width);
  };

  const elapsed = (progress * duration).toFixed(1);
  const total = duration.toFixed(1);

  return (
    <div className="flex items-center gap-3 px-5 py-2.5 border-t border-white/10 bg-panel/40">
      <button
        onClick={controls.toggle}
        title={isPlaying ? 'Pause' : 'Play'}
        className="grid place-items-center w-9 h-9 rounded-lg bg-accent text-canvas hover:brightness-110 transition"
      >
        {isPlaying ? <PauseIcon className="w-5 h-5" /> : <PlayIcon className="w-5 h-5" />}
      </button>
      <button
        onClick={controls.restart}
        title="Restart"
        className="grid place-items-center w-9 h-9 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 transition"
      >
        <RestartIcon className="w-4 h-4" />
      </button>

      <div className="group flex-1 h-2.5 flex items-center cursor-pointer" onClick={onSeek}>
        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-75"
            style={{ width: `${Math.min(100, progress * 100)}%` }}
          />
        </div>
      </div>

      <span className="text-xs tabular-nums text-slate-400 w-24 text-right">
        {elapsed}s / {total}s
      </span>

      <WarningsBadge />
    </div>
  );
}
