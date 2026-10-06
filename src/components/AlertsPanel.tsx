import { ChevronRight, TriangleAlert, CircleCheck, Activity } from 'lucide-react';
import Panel from './Panel';
import { useDashboard } from '../app/DashboardContext';
import { display } from '../services/data';
import { isRecord } from '../services/api';
import { ResourceState } from './ApiState';
import '../styles/insights.css';

function alertText(value: unknown) {
  if (typeof value === 'string') return value;
  if (isRecord(value)) return display(value.message ?? value.title ?? value.description ?? value);
  return display(value);
}
function guidance(message: string) {
  if (/high temperature/i.test(message)) return 'Review the temperature reading and cooling controls.';
  if (/dry soil/i.test(message)) return 'Check soil moisture before approving irrigation.';
  if (/low light/i.test(message)) return 'Review the plant’s lighting conditions.';
  if (/ph/i.test(message)) return 'Verify the pH reading and inspect growing conditions.';
  if (/disease/i.test(message)) return 'Review camera analysis and inspect the affected plant.';
  return 'Review the latest readings before taking action.';
}
export default function AlertsPanel({ onViewAll }: { onViewAll?: () => void }) {
  const { analysis } = useDashboard();
  const waiting = analysis.data?.status === 'waiting';
  const raw = analysis.data?.alerts;
  const known = Array.isArray(raw);
  const alerts = known ? raw.map(alertText) : raw == null ? [] : [alertText(raw)];
  const visible = onViewAll ? alerts.slice(0, 3) : alerts;
  return <Panel title="Plant alerts" className="alerts-panel" action={onViewAll && <button className="text-action" onClick={onViewAll}>View all <ChevronRight size={12}/></button>}>
    <div className="insight-content">
      <ResourceState resource={analysis}/>
      {analysis.error && analysis.data && <p className="insight-note">Showing the last available analysis. It may be out of date.</p>}
      {waiting ? <div className="insight-empty"><Activity size={26}/><h3>Waiting for readings</h3><p>{display(analysis.data?.message ?? 'Alerts will appear when sensor data arrives.')}</p></div> : analysis.data && <>
        <div className="insight-overview"><span className={`insight-badge ${alerts.length ? 'attention' : ''}`}>{alerts.length ? 'Needs review' : known ? 'No active alerts' : 'Status unavailable'}</span><span>{alerts.length} alert{alerts.length === 1 ? '' : 's'}</span></div>
        {alerts.length ? <ul className="insight-alerts">{visible.map((message, index) => <li className="insight-alert" key={`${message}-${index}`}><span className="insight-icon"><TriangleAlert size={19}/></span><div><span className="insight-kicker">{ /disease/i.test(message) ? 'Camera detection' : 'Growing conditions' }</span><h3>{message}</h3><p>{guidance(message)}</p></div></li>)}</ul> : <div className="insight-empty"><CircleCheck size={28}/><h3>{known ? 'No issues flagged' : 'Analysis unavailable'}</h3><p>{known ? 'The latest analysis reported no active alerts.' : 'No alert list was returned. Check again after the next update.'}</p></div>}
        {onViewAll && alerts.length > visible.length && <button className="text-action" onClick={onViewAll}>View {alerts.length - visible.length} more alerts <ChevronRight size={14}/></button>}
      </>}
    </div>
  </Panel>;
}
