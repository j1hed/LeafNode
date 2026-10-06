import Panel from './Panel';
import SensorCards from './SensorCards';
import TrendsPanel from './TrendsPanel';
import AiAgentsPanel from './AiAgentsPanel';
import CameraAnalysis, { DetectionAnalysis } from './CameraAnalysis';
import ActuatorStatus from './ActuatorStatus';
import ManualControls from './ManualControls';
import RecommendationPanel from './RecommendationPanel';
import AlertsPanel from './AlertsPanel';
import HistoryLog from './HistoryLog';
import { useDashboard } from '../app/DashboardContext';
import { API_BASE } from '../services/api';
import { JsonData, ResourceState } from './ApiState';
function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return <div className="workspace-heading"><div><h1>{title}</h1><p>{subtitle}</p></div></div>;
}
export function SensorsPage() {
  const { latest } = useDashboard();
  return <div className="workspace-page"><PageHeader title="Sensors" subtitle="Growing conditions and sensor history."/><SensorCards trends/>
    <div className="two-col-workspace"><TrendsPanel/><Panel title="Latest Sensor Details"><ResourceState resource={latest} empty={!latest.data?.esp32} message="Waiting for sensor data."/>{latest.data?.esp32 && <JsonData value={latest.data.esp32}/>}</Panel></div></div>;
}
export function AgentsPage({ onDetails }: { onDetails: () => void }) {
  return <div className="workspace-page"><PageHeader title="AI Agents" subtitle="Backend analysis and recommended actions."/><AiAgentsPanel onDetails={onDetails}/></div>;
}
export function CameraPage() {
  return <div className="workspace-page"><PageHeader title="Camera Analysis" subtitle="Latest Jetson detection."/><div className="camera-workspace"><CameraAnalysis/><DetectionAnalysis/></div></div>;
}
export function ActuatorsPage() {
  return <div className="workspace-page"><PageHeader title="Actuators" subtitle="Queue manual commands and inspect backend command status."/><div className="actuator-workspace"><ActuatorStatus/><ManualControls/></div></div>;
}
export function RecommendationsPage() {
  return <div className="workspace-page"><PageHeader title="Recommendations" subtitle="Generate guidance for your plant and review it before approval."/><div className="recommendation-workspace"><RecommendationPanel/><Panel title="Validation Workflow"><div className="validation-card"><h3>Human validation is required</h3><p>Generate a recommendation, review its complete content, then approve to queue actions or reject it. Queued actions remain pending until execution is reported.</p></div></Panel></div></div>;
}
export function HistoryPage() { return <div className="workspace-page"><PageHeader title="History" subtitle="Sensor and detection records supplied by the backend."/><HistoryLog full/></div>; }
export function AlertsPage() { return <div className="workspace-page"><PageHeader title="Alerts" subtitle="Current backend analysis alerts."/><AlertsPanel/></div>; }
export function SettingsPage() {
  return <div className="workspace-page"><PageHeader title="Settings" subtitle="LeafNode connection settings."/><div className="settings-grid"><Panel title="Data Source">
    <div className="setting-row"><div><strong>API Base URL</strong><span>Configured with VITE_API_BASE_URL</span></div><code>{API_BASE}</code></div>
    <div className="setting-row"><strong>Latest data</strong><code>/api/latest</code></div>
    <div className="setting-row"><strong>Data mode</strong><span>Live API</span></div>
  </Panel><Panel title="Runtime Preferences"><div className="setting-row"><strong>Refresh cadence</strong><span>5 seconds after completion</span></div><div className="setting-row"><strong>Hardware actions</strong><span>Explicit approval or manual click required</span></div></Panel></div></div>;
}

