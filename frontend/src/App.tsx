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
