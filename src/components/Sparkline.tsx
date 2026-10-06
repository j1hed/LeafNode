type Props = { values: number[]; color: string };
export default function Sparkline({ values, color }: Props) {
  if (!values.length) return <span className="metric-caption">No history</span>;
  const min = Math.min(...values), max = Math.max(...values);
  const points = values.map((value, index) => ({ x: index * (100 / Math.max(1, values.length - 1)), y: 29 - ((value - min) / ((max - min) || 1)) * 20 }));
  return <svg className="sparkline" viewBox="-2 0 104 32" preserveAspectRatio="none" aria-hidden="true">
    <polyline points={points.map(point => point.x + ',' + point.y).join(' ')} fill="none" stroke={color} strokeWidth="1.7" vectorEffect="non-scaling-stroke"/>
    {points.length === 1 && <circle cx={points[0].x} cy={points[0].y} r="1.5" fill={color}/>}
  </svg>;
}
