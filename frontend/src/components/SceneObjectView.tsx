import type { AssetInfo, SceneObject } from '../types/scene';

interface Props {
  object: SceneObject;
  asset?: AssetInfo;
}

// Position, opacity and scale are controlled imperatively by the animation
// engine (see animation/engine.ts) via GSAP, so this component only lays the
// icon out around the origin. The group starts hidden to avoid a flash before
// the engine's first frame.
export default function SceneObjectView({ object, asset }: Props) {
  const w = object.size?.width ?? 96;
  const h = object.size?.height ?? 96;
  const ring = Math.max(w, h) / 2 + 10;

  return (
    <g id={`obj-${object.id}`} className="scene-object" style={{ opacity: 0 }} data-state={object.state}>
      <circle id={`ring-${object.id}`} className="status-ring" r={ring} />
      <g id={`icon-${object.id}`}>
        {asset ? (
          <svg
            x={-w / 2}
            y={-h / 2}
            width={w}
            height={h}
            viewBox={asset.view_box}
            dangerouslySetInnerHTML={{ __html: asset.svg }}
          />
        ) : (
          <g>
            <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={16} fill="#475569" />
            <text textAnchor="middle" dominantBaseline="middle" fontSize="11" fill="#e2e8f0">
              {object.type}
            </text>
          </g>
        )}
      </g>
      <text className="scene-object-label" textAnchor="middle" y={h / 2 + 24}>
        {object.label}
      </text>
    </g>
  );
}
