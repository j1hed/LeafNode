import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { api, type ApiRecord, type Latest, type History, type Commands, type Session } from '../services/api';
import { manualOptions } from '../services/data';

export type Resource<T> = { data: T | null; loading: boolean; error: string | null };
const empty = <T,>(): Resource<T> => ({ data: null, loading: true, error: null });
type Resources = {
  status: Resource<ApiRecord>; latest: Resource<Latest>; sensors: Resource<History>;
  detections: Resource<History>; analysis: Resource<ApiRecord>; commands: Resource<Commands>;
};
const initial = (): Resources => ({ status: empty(), latest: empty(), sensors: empty(), detections: empty(), analysis: empty(), commands: empty() });
export function useDashboardState() {
  const [resources, setResources] = useState(initial);
  const [schema, setSchema] = useState<Resource<ApiRecord>>(empty);
  const [synced, setSynced] = useState<string | null>(null);
  const [plant, setPlant] = useState('tomato');
  const [currentSession, setSession] = useState<Session | null>(null);
  const [sessionPlant, setSessionPlant] = useState('');
  const [busy, setBusy] = useState(false);
  const [workflowError, setWorkflowError] = useState('');
  const [notice, setNotice] = useState('');
  const [decision, setDecision] = useState('');
  const lock = useRef(false);
  const lifetime = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    lifetime.current = controller;
    let timer: ReturnType<typeof setTimeout>;
    let inFlight = false;
    async function poll() {
      if (inFlight || controller.signal.aborted) return;
      inFlight = true;
      const loaders = {
        status: () => api.status(controller.signal), latest: () => api.latest(controller.signal),
        sensors: () => api.history('sensors', controller.signal), detections: () => api.history('detections', controller.signal),
        analysis: () => api.analysis(controller.signal), commands: () => api.commands(controller.signal),
      };
      const entries = Object.entries(loaders);
      const results = await Promise.allSettled(entries.map(([, load]) => load()));
      if (controller.signal.aborted) return;
      setResources(previous => {
        const next = { ...previous };
        entries.forEach(([key], index) => {
          const result = results[index];
          Object.assign(next, { [key]: result.status === 'fulfilled'
            ? { data: result.value, loading: false, error: null }
            : { data: null, loading: false, error: result.reason instanceof Error ? result.reason.message : 'Request failed.' } });
        });
        return next;
      });
      if (results.every(result => result.status === 'fulfilled')) setSynced(new Date().toLocaleString());
      inFlight = false;
      timer = setTimeout(poll, 1000);
    }
    void poll();
    void api.schema(controller.signal).then(data => {
      if (!controller.signal.aborted) setSchema({ data, loading: false, error: null });
    }).catch(error => {
      if (!controller.signal.aborted) setSchema({ data: null, loading: false, error: error.message });
    });
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);

  async function run(work: (signal: AbortSignal) => Promise<void>) {
    const signal = lifetime.current?.signal;
    if (lock.current || !signal || signal.aborted) return;
    lock.current = true; setBusy(true); setWorkflowError(''); setNotice('');
    try { await work(signal); }
    catch (error) { if (!signal.aborted) setWorkflowError(error instanceof Error ? error.message : 'Request failed.'); }
    finally { lock.current = false; if (!signal.aborted) setBusy(false); }
  }
  const generate = () => run(async signal => {
    setSession(null); setDecision(''); setSessionPlant(plant.trim());
    const created = await api.createSession(plant.trim(), signal);
    if (signal.aborted) return;
    setSession(created);
    const generated = await api.generate(created.id, signal);
    if (!signal.aborted) setSession(generated);
  });
  const refreshSession = () => run(async signal => {
    if (!currentSession) return;
    const value = await api.getSession(currentSession.id, signal);
    if (!signal.aborted) setSession(value);
  });
  const decide = (choice: 'approve' | 'reject') => run(async signal => {
    if (!currentSession || decision || currentSession.recommendation_json == null) return;
    // Lock this session even if the response is lost: a timed-out POST may have succeeded.
    setDecision('Outcome unconfirmed');
    await api.decide(currentSession.id, choice, signal);
    if (signal.aborted) return;
    setDecision(choice === 'approve' ? 'Approved — actions pending' : 'Rejected');
    setNotice(choice === 'approve' ? 'Approval accepted. Recommended hardware actions are pending, not confirmed executed.' : 'Recommendation rejected.');
    const value = await api.getSession(currentSession.id, signal);
    if (!signal.aborted) setSession(value);
  });
  return { ...resources, schema, options: manualOptions(schema.data), synced, plant, setPlant,
    currentSession, sessionPlant, busy, workflowError, notice, decision, generate, refreshSession, decide };
}
type DashboardState = ReturnType<typeof useDashboardState>;
const Context = createContext<DashboardState | null>(null);
export function DashboardProvider({ children }: { children: ReactNode }) {
  const value = useDashboardState();
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useDashboard() {
  const state = useContext(Context);
  if (!state) throw new Error('DashboardProvider is required.');
  return state;
}
