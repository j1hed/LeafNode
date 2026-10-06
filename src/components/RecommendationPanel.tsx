import { Leaf, LoaderCircle } from 'lucide-react';
import Panel from './Panel';
import { useDashboard } from '../app/DashboardContext';
import { display } from '../services/data';
import { isRecord } from '../services/api';
import { JsonData } from './ApiState';
import '../styles/recommendation.css';

const deviceImages: Record<string, string> = {
  pump: '/assets/icons/05_actuators/35_irrigation_pump.png',
  fan: '/assets/icons/05_actuators/36_cooling_fan.png',
  peltier: '/assets/icons/05_actuators/39_peltier_cooling.png',
};
export default function RecommendationPanel() {
  const state = useDashboard();
  const { currentSession, busy, decision } = state;
  const recommendation = currentSession?.recommendation_json;
  const result = isRecord(recommendation) ? recommendation : null;
  const actions = Array.isArray(result?.actions) ? result.actions : [];
  const firstDevice = actions.find(action => isRecord(action) && typeof action.device === 'string' && deviceImages[action.device]);
  const device = isRecord(firstDevice) ? String(firstDevice.device) : '';
  const illustration = deviceImages[device] ?? '/assets/landing/plant.png';
  return <Panel title="Agronomic Recommendation" className="recommendation-panel" icon={<Leaf size={18}/>}>
    <div className="recommendation-copy">
      <div className="recommendation-visual" key={`visual-${currentSession?.id ?? 'empty'}-${device}`}>
        <div className="recommendation-art"><img src={illustration} alt={device ? `${device} illustration for a suggested action` : 'Plant care illustration'} width="150" height="150"/><span>Illustration</span></div>
        <div><span className="recommendation-eyebrow">Personalized plant care</span><h3>{result ? `Care plan for ${state.sessionPlant || 'your plant'}` : 'Help your plants thrive'}</h3><p>{result ? 'Review your recommendation and suggested actions below.' : 'Turn your latest growing conditions into a care plan you can review.'}</p></div>
      </div>
      <label className="api-field">Plant type<input value={state.plant} list="plant-types" onChange={event => state.setPlant(event.target.value)} disabled={busy}/></label>
      <datalist id="plant-types"><option value="tomato"/></datalist>
      <button className="primary-btn recommendation-generate" disabled={busy || !state.plant.trim()} onClick={() => void state.generate()}>{busy ? <LoaderCircle className="recommendation-spinner" size={16}/> : <Leaf size={16}/>} {busy ? 'Working…' : 'Generate recommendation'}</button>
      {busy && <div className="recommendation-progress" role="status"><span/>Updating your care plan…</div>}
      {!currentSession && !busy && <p className="api-state">Choose a plant to get started.</p>}
      {currentSession && <>
        <p className="api-state">Session {currentSession.id} · {state.sessionPlant} · {decision || display(currentSession.status)}</p>
        {recommendation == null ? <p className="api-state">Waiting for a recommendation. Refresh this session to check its progress.</p> : result ? <div className="recommendation-result" key={currentSession.id}>
          {result.summary != null && <div className="recommendation-summary"><span className="recommendation-eyebrow">Your care summary</span><p>{display(result.summary)}</p></div>}
          {['care_guide', 'disease_notes'].map(field => result[field] ? <section className="recommendation-guidance" key={field}><h3>{field === 'care_guide' ? 'How to care for your plant' : 'Plant health notes'}</h3><p>{display(result[field])}</p></section> : null)}
          {Array.isArray(result.alerts) && result.alerts.length > 0 && <section className="recommendation-guidance"><h3>Things to watch</h3><ul>{result.alerts.map((alert, index) => <li key={index}>{display(alert)}</li>)}</ul></section>}
          {actions.length > 0 && <section className="recommendation-guidance"><h3>Suggested actions</h3><div className="recommendation-action-cards">{actions.map((value, index) => {
            const action = isRecord(value) ? value : null;
            const actionDevice = String(action?.device ?? '');
            return <article className="recommendation-action-card" key={index}><img src={deviceImages[actionDevice] ?? '/assets/icons/01_navigation_brand/07_recommendations_leaf.png'} alt="" width="52" height="52"/><div><h4>{action ? `${display(action.device)} · ${display(action.action)}` : 'Suggested action'}</h4><p>{action ? display(action.reason ?? 'Review before approving.') : display(value)}</p>{action?.duration_minutes != null && <span>{display(action.duration_minutes)} minutes</span>}</div></article>;
          })}</div></section>}
          <details><summary>Complete recommendation</summary><JsonData value={recommendation}/></details>
        </div> : <JsonData value={recommendation}/>}
        <div className="api-actions">
          <button className="primary-btn" disabled={busy || !!decision || recommendation == null} onClick={() => void state.decide('approve')}>Approve &amp; queue actions</button>
          <button className="secondary-btn" disabled={busy || !!decision || recommendation == null} onClick={() => void state.decide('reject')}>Reject</button>
          <button className="secondary-btn" disabled={busy} onClick={() => void state.refreshSession()}>Refresh session</button>
        </div>
        <details><summary>Session details</summary><JsonData value={currentSession}/></details>
      </>}
      <p className="api-state">Approval queues hardware actions. Execution is not confirmed by approval.</p>
      {state.workflowError && <p className="api-state api-error" role="alert">{state.workflowError} If a request failed after submission, check the session and command queue before trying again.</p>}
      {state.notice && <p className="api-state" role="status">{state.notice}</p>}
    </div>
  </Panel>;
}
