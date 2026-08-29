import { useMemo } from 'react';
import type { RefObject } from 'react';
import { useSceneStore } from '../store/sceneStore';
import type { SceneObject } from '../types/scene';
import EdgeView from './EdgeView';
import SceneObjectView from './SceneObjectView';

interface Props {
  svgRef: RefObject<SVGSVGElement>;
}

export default function SceneCanvas({ svgRef }: Props) {
  const scene = useSceneStore((s) => s.scene);
  const assets = useSceneStore((s) => s.assets);

  const objectMap = useMemo(() => {
    const map: Record<string, SceneObject> = {};
    if (scene) for (const obj of scene.objects) map[obj.id] = obj;
    return map;
  }, [scene]);

  const width = scene?.canvas.width ?? 1280;
  const height = scene?.canvas.height ?? 720;
  const background = scene?.canvas.background ?? '#0b1020';

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ background }}
    >
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M0 0 L10 5 L0 10 z" fill="#7f8bb5" />
        </marker>
        <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {scene && (
        <g id="camera">
          <g className="edges" key={`edges-${scene.id}`}>
            {scene.edges.map((edge) => (
              <EdgeView key={edge.id} edge={edge} from={objectMap[edge.from]} to={objectMap[edge.to]} />
            ))}
          </g>
          <g className="objects" key={`objects-${scene.id}`}>
            {scene.objects.map((obj) => (
              <SceneObjectView key={obj.id} object={obj} asset={assets[obj.type]} />
            ))}
          </g>
        </g>
      )}
    </svg>
  );
}
