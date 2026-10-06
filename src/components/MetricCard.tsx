import type { CSSProperties } from 'react';
import IconImage from './IconImage';
import Sparkline from './Sparkline';

type Props = {
  label: string;
  value: string;
  unit: string;
  icon: string;
  color: string;
  values: number[];
  showTrend?: boolean;
};

export default function MetricCard({ label, value, unit, icon, color, values, showTrend = true }: Props) {
  return (
    <article className={'metric-card ' + (showTrend ? 'has-trend' : '')} style={{ '--metric-accent': color } as CSSProperties}>
      <div className="metric-top"><span>{label}</span><IconImage src={icon} className="metric-icon" /></div>
      <div className="metric-value"><strong>{value}</strong><em>{unit}</em></div>
      {showTrend ? <Sparkline values={values} color={color} /> : <span className="metric-caption">Latest reading</span>}
    </article>
  );
}
