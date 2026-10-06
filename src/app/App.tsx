import '../styles/api.css';
import { useEffect, useRef, useState } from 'react';
import Sidebar, { type ViewName } from '../components/Sidebar';
import TopStatusBar from '../components/TopStatusBar';
import SensorCards from '../components/SensorCards';
import AiAgentsPanel from '../components/AiAgentsPanel';
import CameraAnalysis from '../components/CameraAnalysis';
import { ArrowUpRight, ChevronDown } from 'lucide-react';
import ActuatorStatus from '../components/ActuatorStatus';
import ManualControls from '../components/ManualControls';
import RecommendationPanel from '../components/RecommendationPanel';
import AlertsPanel from '../components/AlertsPanel';
import HistoryLog from '../components/HistoryLog';
import BottomStatusBar from '../components/BottomStatusBar';
import Modal from '../components/Modal';
import { AgentsPage, AlertsPage, ActuatorsPage, CameraPage, HistoryPage, RecommendationsPage, SensorsPage, SettingsPage } from '../components/SecondaryPages';
import { DashboardProvider, useDashboard } from './DashboardContext';
import { api } from '../services/api';
import { JsonData, ResourceState } from '../components/ApiState';
import { display } from '../services/data';

function Dashboard({ setView, openAgents }: { setView: (view: ViewName) => void; openAgents: () => void }) {
  const { status } = useDashboard();
  return <div className="dashboard-view">
    <header className="dashboard-heading"><div><span className="eyebrow">Your growing space</span><h1>Greenhouse overview</h1><p>A little insight. A healthier growing space.</p></div>
      <div className="heading-actions"><div className={'workspace-state ' + (status.error ? 'is-offline' : '')}><span/><strong>{status.loading ? 'Connecting…' : status.error ? 'Connection error' : 'Backend: ' + display(status.data?.status)}</strong></div><button className="primary-btn" onClick={() => setView('Sensors')}>Explore sensors <ArrowUpRight size={16}/></button></div></header>
    <section className="dashboard-section" aria-labelledby="conditions-title"><div className="section-heading"><h2 id="conditions-title">Growing conditions</h2><span>Latest sensor readings</span></div><SensorCards/></section>
    <div className="overview-grid"><CameraAnalysis/><AlertsPanel onViewAll={() => setView('Alerts')}/></div>
    <section className="dashboard-section" aria-labelledby="controls-title"><div className="section-heading"><h2 id="controls-title">Greenhouse controls</h2><span>Actions require your click</span></div><div className="controls-layout"><ActuatorStatus/><ManualControls/></div></section>
    <div className="insights-grid"><RecommendationPanel/><AiAgentsPanel onDetails={openAgents}/></div>
    <details className="dashboard-details"><summary><span>System connections</span><span>Devices &amp; connectivity <ChevronDown size={16}/></span></summary><TopStatusBar/></details>
    <details className="dashboard-details"><summary><span>Recent activity</span><span>Sensor &amp; detection history <ChevronDown size={16}/></span></summary><HistoryLog/></details>
  </div>;
}
function DashboardShell() {
  const mainContentRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<ViewName>('Dashboard');
  const [collapsed, setCollapsed] = useState(false);
  const [agentModal, setAgentModal] = useState(false);
  const state = useDashboard();
  useEffect(() => { mainContentRef.current?.scrollTo({ top: 0, left: 0 }); }, [view]);
  const openAgents = () => setAgentModal(true);
  const pages = {
    Sensors: <SensorsPage/>, 'AI Agents': <AgentsPage onDetails={openAgents}/>,
    'Camera Analysis': <CameraPage/>, Actuators: <ActuatorsPage/>, Recommendations: <RecommendationsPage/>,
    History: <HistoryPage/>, Alerts: <AlertsPage/>, Settings: <SettingsPage/>,
    Dashboard: <Dashboard setView={setView} openAgents={openAgents}/>,
  };
  const errors = ['status', 'latest', 'sensors', 'detections', 'analysis', 'commands'].filter(key => state[key as 'status'].error);
  const logout = async () => { await api.logout().catch(() => undefined); window.location.hash = '#/dashboard'; };
  return <div className={'leafnode-app ' + (collapsed ? 'sidebar-is-collapsed' : '')}>
    <Sidebar active={view} onNavigate={setView} collapsed={collapsed} onToggleCollapse={() => setCollapsed(value => !value)} onLogout={logout}/>
    <main className="main-shell"><div className="main-content" ref={mainContentRef}>
      {errors.length > 0 && <p className="api-state api-error" role="alert">Could not refresh: {errors.join(', ')}. Retrying automatically. Missing readings are unavailable.</p>}
      {pages[view]}
    </div><BottomStatusBar/></main>
    {agentModal && <Modal title="Backend Analysis" onClose={() => setAgentModal(false)}><ResourceState resource={state.analysis}/>{state.analysis.data && <JsonData value={state.analysis.data}/>}</Modal>}
  </div>;
}
export default function App() { return <DashboardProvider><DashboardShell/></DashboardProvider>; }
