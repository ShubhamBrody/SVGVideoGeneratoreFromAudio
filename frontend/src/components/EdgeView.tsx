import type { SceneEdge, SceneObject } from '../types/scene';

const TRAFFIC_COLORS: Record<string, string> = {
  traffic: '#38bdf8',
  data: '#22c55e',
  control: '#f59e0b',
  dependency: '#a78bfa',
  solid: '#7f8bb5',
  dashed: '#7f8bb5',
};

interface Props {
  edge: SceneEdge;
  from?: SceneObject;
  to?: SceneObject;
}

// Draws a trimmed line between two object centers. The base line and the
// animated "traffic" overlay start hidden; the engine reveals them on the
// connect / traffic timeline actions.
export default function EdgeView({ edge, from, to }: Props) {
  if (!from || !to) return null;

  const trimStart = 52;
  const trimEnd = 60;
  const dx = to.position.x - from.position.x;
  const dy = to.position.y - from.position.y;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;

  const x1 = from.position.x + ux * trimStart;
  const y1 = from.position.y + uy * trimStart;
  const x2 = to.position.x - ux * trimEnd;
  const y2 = to.position.y - uy * trimEnd;
  const d = `M ${x1.toFixed(1)} ${y1.toFixed(1)} L ${x2.toFixed(1)} ${y2.toFixed(1)}`;

  const color = TRAFFIC_COLORS[edge.style] ?? '#38bdf8';
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;

  return (
    <g id={`edge-${edge.id}`} className="edge">
      <path
        id={`edge-path-${edge.id}`}
        className="edge-line"
        d={d}
        markerEnd="url(#arrow)"
        style={{ opacity: 0 }}
      />
      <path id={`edge-traffic-${edge.id}`} className="edge-traffic" d={d} style={{ stroke: color }} />
      {edge.label ? (
        <text x={midX} y={midY - 8} textAnchor="middle" fontSize="13" fill="#93a0c8">
          {edge.label}
        </text>
      ) : null}
    </g>
  );
}
