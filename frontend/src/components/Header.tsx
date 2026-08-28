import { useSceneStore } from '../store/sceneStore';
import { FilmIcon } from './icons';

export default function Header() {
  const scene = useSceneStore((s) => s.scene);
  const provider = useSceneStore((s) => s.provider);

  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-panel/60 backdrop-blur">
      <div className="flex items-center gap-3">
        <span className="grid place-items-center w-8 h-8 rounded-lg bg-accent/15 text-accent">
          <FilmIcon className="w-5 h-5" />
        </span>
        <div className="leading-tight">
          <h1 className="text-sm font-semibold tracking-wide">
            SVG Video Generator <span className="text-slate-400 font-normal">from Audio</span>
          </h1>
          <p className="text-xs text-slate-400">
            {scene ? scene.title : 'Speak or type a technical concept to animate it'}
          </p>
        </div>
      </div>
      {provider ? (
        <span className="text-[11px] px-2 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10">
          provider: {provider}
        </span>
      ) : null}
    </header>
  );
}
