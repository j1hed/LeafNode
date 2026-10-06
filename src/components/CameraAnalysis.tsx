import { Camera, Clock, ScanLine } from 'lucide-react';
import Panel from './Panel';
import { useDashboard } from '../app/DashboardContext';
import { display, reading } from '../services/data';
import { ResourceState, JsonData } from './ApiState';
import { isRecord } from '../services/api';
import '../styles/insights.css';

export default function CameraAnalysis() {
  const { latest } = useDashboard();
  const detection = latest.data?.jetson;
  const raw = reading(detection?.confidence);
  const confidence = raw !== null && raw >= 0 && raw <= 100 ? raw : null;
  const condition = typeof detection?.disease === 'string' ? detection.disease.replace(/_/g, ' ').trim() : '';
  const healthy = condition.toLowerCase() === 'healthy';
  const time = detection ? [detection.date, detection.hour].filter(value => typeof value === 'string').join(' ') || display(detection.timestamp) : '';
  return <Panel title="Camera analysis" className="camera-panel" action={<span className="insight-source">Jetson camera</span>}>
    <div className="insight-content">
      <ResourceState resource={latest}/>
      {latest.error && detection && <p className="insight-note">Showing the last available detection. It may be out of date.</p>}
      {detection ? <>
        <div className={`detection-hero ${healthy ? 'is-healthy' : ''}`}><div className="detection-symbol"><ScanLine size={32}/></div><span className="insight-kicker">Latest detected condition</span><h3>{condition || 'Condition unavailable'}</h3><span className={`insight-badge ${healthy || !condition ? '' : 'attention'}`}>{healthy ? 'Healthy classification' : condition ? 'Review detection' : 'Awaiting classification'}</span></div>
        <div className="detection-confidence"><div><span>Model confidence</span><strong>{confidence === null ? 'Unavailable' : `${confidence.toFixed(1)}%`}</strong></div>{confidence !== null && <meter min={0} max={100} value={confidence} aria-label="Detection confidence"/>}<p>Confidence describes the model’s prediction, not a confirmed diagnosis.</p></div>
        <div className="detection-time"><Clock size={15}/><span>Captured: {time}</span></div>
      </> : !latest.loading && !latest.error && <div className="insight-empty"><ScanLine size={32}/><h3>No detection yet</h3><p>The latest condition and confidence will appear when Jetson sends a result.</p></div>}
      <div className="camera-availability"><Camera size={20}/><div><strong>Image preview unavailable</strong><p>The camera currently sends detection results without an image.</p></div></div>
    </div>
  </Panel>;
}

export function DetectionAnalysis() {
  const { analysis } = useDashboard();
  const detection = isRecord(analysis.data?.ai_detection) ? analysis.data.ai_detection : null;
  return <Panel title="Detection details"><div className="insight-content"><ResourceState resource={analysis}/>
    {analysis.error && detection && <p className="insight-note">Showing the last available analysis. It may be out of date.</p>}
    {detection ? <><dl className="detection-details">{[['Condition', detection.disease], ['Confidence', typeof detection.confidence === 'number' ? `${detection.confidence}%` : null], ['Date', detection.date], ['Time', detection.hour]].map(([label, value]) => <div key={String(label)}><dt>{String(label)}</dt><dd>{display(value)}</dd></div>)}</dl><div className="detection-guidance"><h3>Review the result</h3><p>Compare this classification with the plant’s visible condition. Use Recommendations to request care guidance and review any actions before approval.</p></div><details className="detection-raw"><summary>Technical details</summary><JsonData value={detection}/></details></> : !analysis.loading && !analysis.error && <div className="insight-empty"><ScanLine size={28}/><h3>Waiting for analysis</h3><p>Detection details will appear when the backend returns an analyzed result.</p></div>}
  </div></Panel>;
}

