type Props = { label: string; values: number[]; color: string; current: string; labels?: string[]; showTime?: boolean };
export default function TelemetryChart({ label, values, color, current, labels = [], showTime = false }: Props) {
  const min = Math.min(...values), max = Math.max(...values);
  const points = values.map((value, index) => {
    const x = 8 + index * (82 / Math.max(1, values.length - 1));
    const y = 43 - ((value - min) / ((max - min) || 1)) * 24;
    return { x, y };
  });
  return <div className="telemetry-chart"><div className="chart-label">{label}</div><div className="chart-current" style={{ borderColor: color, color }}>{current}</div>
    {values.length ? <svg viewBox="0 0 100 54" preserveAspectRatio="none" aria-label={label + ' telemetry chart'}>
      {[15, 28, 41].map(y => <line key={y} x1="7" x2="91" y1={y} y2={y} className="grid-line"/>)}
      <polyline points={points.map(point => point.x + ',' + point.y).join(' ')} fill="none" stroke={color} strokeWidth="1.4" vectorEffect="non-scaling-stroke"/>
      {points.length === 1 && <circle cx={points[0].x} cy={points[0].y} r="1.5" fill={color}/>}
    </svg> : <p className="api-state">No numeric history for this channel.</p>}
    {showTime && <div className="time-axis">{labels.map((label, index) => <span key={index}>{label}</span>)}</div>}
  </div>;
}
