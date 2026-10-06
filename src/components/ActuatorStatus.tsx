import { Clock, Radio, CheckCircle, CircleAlert } from 'lucide-react';
import Panel from './Panel';
import { useDashboard } from '../app/DashboardContext';
import { isRecord } from '../services/api';
import { display } from '../services/data';
import { JsonData, ResourceState } from './ApiState';
import '../styles/controller.css';

export default function ActuatorStatus() {
  const { commands } = useDashboard();
  const rows = commands.data?.commands ?? [];
  const pending = rows.filter(row => isRecord(row) && ['queued', 'pending'].includes(String(row.status))).length;
  return <Panel title="Greenhouse command activity" className="actuator-panel" icon={<Radio size={18}/>}>
    <div className="controller-content"><ResourceState resource={commands}/>
      {commands.error && commands.data && <p className="controller-note">Showing the last available command history. It may be out of date.</p>}
      <div className="controller-overview"><span className="controller-pill">{commands.data ? `${pending} pending in loaded history` : 'Awaiting command history'}</span><span>Device-reported results</span></div>
      <p className="controller-note">Commands show requests and acknowledgments. Live pump, fan, and cooling states are not provided by the backend.</p>
      {!rows.length && !commands.loading && !commands.error && <div className="controller-empty"><Clock size={26}/><h3>No commands yet</h3><p>Manual and approved commands will appear here.</p></div>}
      <div className="controller-command-list">{rows.slice(0, 6).map((row, index) => {
        const command = isRecord(row) ? row : {};
        const status = String(command.status ?? 'unknown');
        const queued = status === 'pending' || status === 'queued';
        const done = status === 'executed';
        const label = queued ? 'Pending execution' : done ? 'Execution reported' : status === 'failed' ? 'Failed' : `Status: ${status}`;
        return <article className="controller-command" key={String(command.id ?? index)}><div className="controller-command-head"><h3>{display(command.device)} <span>{display(command.action)}</span></h3><span className={`controller-pill ${done ? 'success' : queued ? 'pending' : 'unknown'}`}>{queued ? <Clock size={12}/> : done ? <CheckCircle size={12}/> : <CircleAlert size={12}/>} {label}</span></div><p>{display(command.reason ?? 'No reason supplied')}</p><div className="controller-command-meta"><span>#{display(command.id)}</span><span>{command.duration_minutes == null ? 'Duration unspecified' : `${display(command.duration_minutes)} min`}</span><span>{display(command.created_at)}</span></div><details className="controller-details"><summary>Command details</summary><JsonData value={row}/></details></article>;
      })}</div>
      {rows.length > 6 && <details className="controller-details"><summary>View {rows.length - 6} earlier commands</summary><JsonData value={rows.slice(6)}/></details>}
    </div>
  </Panel>;
}
