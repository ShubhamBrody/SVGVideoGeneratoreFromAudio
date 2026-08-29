import { useEffect, useRef } from 'react';
import SceneCanvas from './components/SceneCanvas';
import Header from './components/Header';
import PromptBar from './components/PromptBar';
import TimelineControls from './components/TimelineControls';
import SubtitleOverlay from './components/SubtitleOverlay';
import StatusOverlay from './components/StatusOverlay';
import { useSceneAnimation } from './animation/useSceneAnimation';
import { useSceneStore } from './store/sceneStore';

export default function App() {
  const svgRef = useRef<SVGSVGElement>(null);
  const controls = useSceneAnimation(svgRef);
  const loadAssets = useSceneStore((s) => s.loadAssets);

  useEffect(() => {
    void loadAssets();
  }, [loadAssets]);

  // Chrome-free full-bleed playback for the video recorder (URL: /?render).
  const renderMode =
    typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('render');

  if (renderMode) {
    return (
      <div className="h-screen w-screen bg-canvas text-slate-100">
        <main className="relative w-full h-full overflow-hidden">
          <SceneCanvas svgRef={svgRef} />
          <SubtitleOverlay />
        </main>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-canvas text-slate-100">
      <Header />
      <main className="relative flex-1 overflow-hidden">
        <SceneCanvas svgRef={svgRef} />
        <StatusOverlay />
        <SubtitleOverlay />
      </main>
      <TimelineControls controls={controls} />
      <PromptBar />
    </div>
  );
}
