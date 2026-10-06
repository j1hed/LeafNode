import { Activity, BrainCircuit, ArrowRight, CircleCheck } from 'lucide-react';
import Panel from './Panel';
import { useDashboard } from '../app/DashboardContext';
import { display } from '../services/data';
import { isRecord } from '../services/api';
import { JsonData, ResourceState } from './ApiState';
import '../styles/controller.css';

export default function AiAgentsPanel({ onDetails }: { onDetails: () => void }) {
  const { analysis } = useDashboard();
  const data = analysis.data;
  const waiting = data?.status === 'waiting';
  const normal = data?.system_state === 'NORMAL';
  const actions = Array.isArray(data?.recommended_actions) ? data.recommended_actions : null;
  const alerts = Array.isArray(data?.alerts) ? data.alerts : null;
  return <Panel title="AI analysis" className="agents-panel" icon={<BrainCircuit size={18}/>} action={<button className="text-action" onClick={onDetails}>Explore analysis <ArrowRight size={13}/></button>}>
    <div className="controller-content"><ResourceState resource={analysis}/>
      {analysis.error && data && <p className="controller-note">Last available analysis shown. Results may be out of date.</p>}
      {waiting ? <div className="controller-empty"><Activity size={28}/><h3>Waiting for growing conditions</h3><p>{display(data?.message ?? 'Analysis will appear when sensor readings arrive.')}</p></div> : data && <>
        <div className={`analysis-verdict ${normal ? 'normal' : ''}`}><span className="controller-symbol">{normal ? <CircleCheck size={24}/> : <Activity size={24}/>}</span><div><span className="controller-eyebrow">Greenhouse assessment</span><h3>{normal ? 'Conditions look stable' : data.system_state === 'ATTENTION' ? 'Your plants need a closer look' : 'Assessment unavailable'}</h3><p>{normal ? 'No issues flagged by the latest backend analysis.' : 'Review the findings and suggested actions below.'}</p></div></div>
        <div className="analysis-metrics"><div><strong>{alerts?.length ?? '—'}</strong><span>Active alerts</span></div><div><strong>{actions?.length ?? '—'}</strong><span>Suggested actions</span></div></div>
        <h3 className="controller-subheading">Suggested next steps</h3>
        {actions?.length ? <ol className="analysis-actions">{actions.map((action, index) => <li key={index}><span>{index + 1}</span><p>{typeof action === 'string' ? action : isRecord(action) ? display(action.description ?? action.reason ?? action.action ?? action) : display(action)}</p></li>)}</ol> : <p className="controller-note">{actions ? 'No actions recommended in this analysis.' : 'No action list is available yet.'}</p>}
        <p className="controller-note">Suggestions are for review. Hardware commands require your approval or a manual command.</p>
        <details className="controller-details"><summary>Analysis data</summary><JsonData value={data}/></details>
      </>}
    </div>
  </Panel>;
}
