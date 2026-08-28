import { useState } from 'react';
import { useSceneStore } from '../store/sceneStore';

// Surfaces the deterministic validator's repairs (unknown types remapped,
// dangling edges dropped, etc.) so nothing is silently changed.
export default function WarningsBadge() {
  const warnings = useSceneStore((s) => s.warnings);
  const [open, setOpen] = useState(false);

  if (!warnings.length) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-[11px] px-2 py-1 rounded-full bg-amber-400/10 text-amber-300 border border-amber-400/30 hover:bg-amber-400/20 transition"
      >
        {warnings.length} auto-fix{warnings.length > 1 ? 'es' : ''}
      </button>
      {open && (
        <ul className="absolute bottom-full right-0 mb-2 w-80 max-h-56 overflow-auto p-3 rounded-xl bg-panelling border border-white/10 shadow-xl text-xs text-slate-300 space-y-1.5 z-20">
          {warnings.map((w, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-amber-400">•</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
