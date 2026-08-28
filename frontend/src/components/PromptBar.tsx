import { useState } from 'react';
import { useSceneStore } from '../store/sceneStore';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { MicIcon, SendIcon } from './icons';

const EXAMPLES = [
  'A Kubernetes service routes traffic to five pods, then pod 3 fails and is replaced',
  'Explain how Kafka handles a consumer failure',
  'A user calls an API gateway that talks to a server and a Postgres database',
  'A load balancer distributes requests to three servers with a Redis cache',
];

export default function PromptBar() {
  const [text, setText] = useState('');
  const generate = useSceneStore((s) => s.generate);
  const status = useSceneStore((s) => s.status);
  const scene = useSceneStore((s) => s.scene);

  const busy = status === 'generating' || status === 'transcribing';

  const submit = (value?: string) => {
    const v = (value ?? text).trim();
    if (!v || busy) return;
    setText(v);
    void generate(v);
  };

  const { recording, toggle } = useVoiceRecorder((t) => {
    setText(t);
    submit(t);
  });

  return (
    <div className="px-5 py-3 border-t border-white/10 bg-panel/60 backdrop-blur">
      {!scene && (
        <div className="flex flex-wrap gap-2 mb-3">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => submit(ex)}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 disabled:opacity-50 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-center gap-2"
      >
        <button
          type="button"
          onClick={toggle}
          title={recording ? 'Stop recording' : 'Record voice'}
          className={`grid place-items-center w-11 h-11 shrink-0 rounded-xl border transition-colors ${
            recording
              ? 'bg-red-500/20 border-red-400/50 text-red-300 animate-pulse'
              : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
          }`}
        >
          <MicIcon className="w-5 h-5" />
        </button>

        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe a system, architecture, or protocol to animate…"
          className="flex-1 h-11 px-4 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-accent/60"
        />

        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="grid place-items-center gap-2 h-11 px-4 rounded-xl bg-accent text-canvas font-medium text-sm disabled:opacity-40 hover:brightness-110 transition"
        >
          <SendIcon className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
