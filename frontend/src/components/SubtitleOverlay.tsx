import { useSceneStore } from '../store/sceneStore';

export default function SubtitleOverlay() {
  const subtitle = useSceneStore((s) => s.subtitle);
  if (!subtitle) return null;

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-6 flex justify-center px-6">
      <div className="max-w-2xl text-center text-[15px] leading-snug px-4 py-2 rounded-lg bg-black/55 backdrop-blur-sm text-slate-100 border border-white/10">
        {subtitle}
      </div>
    </div>
  );
}
