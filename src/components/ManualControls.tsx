import { SlidersHorizontal, Send } from 'lucide-react';
import '../styles/controller.css';
import { useEffect, useRef, useState } from 'react';
import Panel from './Panel';
import { api } from '../services/api';
import { useDashboard } from '../app/DashboardContext';
export default function ManualControls() {
  const { options, schema } = useDashboard();
  const [device, setDevice] = useState('');
  const [action, setAction] = useState('');
  const [duration, setDuration] = useState('2');
  const [reason, setReason] = useState('manual override');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const lock = useRef(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const selectedDevice = device || options.devices[0] || '';
  const selectedAction = action || options.actions[0] || '';
  const verified = options.devices.length > 0 && options.actions.length > 0;
  async function send() {
    if (lock.current || uncertain || !options.devices.includes(selectedDevice) || !options.actions.includes(selectedAction) ||
      !Number.isFinite(Number(duration)) || Number(duration) <= 0 || !reason.trim()) return;
    lock.current = true; setBusy(true); setMessage(''); setError('');
    const active = new AbortController(); controller.current = active;
    try {
      const result = await api.manual({ device: selectedDevice, action: selectedAction, duration_minutes: Number(duration), reason: reason.trim() }, active.signal);
      if (!active.signal.aborted) setMessage('Command ' + result.command_id + ' queued — pending execution.');
    } catch (failure) {
      if (!active.signal.aborted) { setError(failure instanceof Error ? failure.message : 'Command request failed.'); setUncertain(true); }
    } finally { lock.current = false; if (!active.signal.aborted) setBusy(false); }
  }
  return <Panel title="Manual greenhouse control" className="controls-panel" icon={<SlidersHorizontal size={18}/>}><div className="controller-content"><p className="controller-intro">Choose a device and queue an action.</p><p className="controller-note">The device must acknowledge the command before execution is confirmed.</p>
    {!verified && <p className="api-state" role="status">{schema.loading ? 'Checking supported controls…' : 'Controls unavailable: supported device and action names could not be verified from the backend API schema.'}</p>}
    <div className="manual-control-fields">
      <label className="api-field">Device<select value={selectedDevice} onChange={event => setDevice(event.target.value)} disabled={!verified || busy}>{!verified && <option value="">Unavailable</option>}{options.devices.map(value => <option key={value}>{value}</option>)}</select></label>
      <label className="api-field">Action<select value={selectedAction} onChange={event => setAction(event.target.value)} disabled={!verified || busy}>{!verified && <option value="">Unavailable</option>}{options.actions.map(value => <option key={value}>{value}</option>)}</select></label>
      <label className="api-field">Duration (minutes)<input type="number" min="0.01" step="any" value={duration} onChange={event => setDuration(event.target.value)} disabled={busy}/></label>
      <label className="api-field">Reason<input value={reason} onChange={event => setReason(event.target.value)} disabled={busy}/></label>
    </div>
    <div className="manual-command-preview"><span className="controller-eyebrow">Command preview</span><strong>{verified ? `${selectedDevice} · ${selectedAction}` : 'Waiting for supported controls'}</strong><p>{Number.isFinite(Number(duration)) && Number(duration) > 0 ? `${duration} minutes` : 'Enter a valid duration'}</p></div><button className="primary-btn manual-send" disabled={!verified || busy || uncertain || !reason.trim() || !Number.isFinite(Number(duration)) || Number(duration) <= 0} onClick={() => void send()}><Send size={15}/>{busy ? 'Queuing…' : 'Queue manual command'}</button>
    {message && <p className="api-state" role="status">{message}</p>}
    {error && <p className="api-state api-error" role="alert">{error} Check the command queue: the request may have been accepted.</p>}
    {uncertain && <button className="secondary-btn" onClick={() => setUncertain(false)}>I checked the queue — enable controls</button>}
  </div></Panel>;
}

