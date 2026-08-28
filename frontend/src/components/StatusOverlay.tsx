import { useSceneStore } from '../store/sceneStore';

export default function StatusOverlay() {
  const status = useSceneStore((s) => s.status);
  const message = useSceneStore((s) => s.statusMessage);
  const scene = useSceneStore((s) => s.scene);

  const busy = status === 'generating' || status === 'transcribing' || status === 'recording';

  if (busy) {
    return (
      <div className="absolute inset-0 grid place-items-center bg-canvas/40 backdrop-blur-[1px]">
        <div className="flex flex-col items-center gap-3">
          <div className="spinner" />
          <p className="text-sm text-slate-300">{message || 'Working…'}</p>
        </div>
      </div>
    );
  }

  if (!scene) {
    return (
      <div className="absolute inset-0 grid place-items-center px-6">
        <div className="text-center max-w-md">
          <h2 className="text-lg font-semibold text-slate-200">Speak. Watch the concept come alive.</h2>
          <p className="mt-2 text-sm text-slate-400">
            Describe a system — Kubernetes, Kafka, an API flow — and it becomes a deterministic,
            animated SVG diagram. Try a suggestion below or press the microphone.
          </p>
          {status === 'error' && message ? (
            <p className="mt-4 text-sm text-red-300">{message}</p>
          ) : null}
        </div>
      </div>
    );
  }

  return null;
}
