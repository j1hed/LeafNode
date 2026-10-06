import { useDashboard } from '../app/DashboardContext';
import { display } from '../services/data';
export default function TopStatusBar() {
  const { status, latest } = useDashboard();
  const rows = [
    ['Backend status', status.loading ? 'Connecting…' : status.error ? 'Connection error' : display(status.data?.status)],
    ['Sensor data', latest.data?.esp32 ? 'Available' : 'Unavailable'],
    ['Detection data', latest.data?.jetson ? 'Available' : 'Unavailable'],
    ['Latest timestamp', display(latest.data?.timestamp)],
    ['Hardware execution', 'Unconfirmed'],
  ];
  return <div className="top-status-grid">{rows.map(([label, value]) => <div className="top-status-card" key={label}><div className="status-copy"><span className="status-label">{label}</span><strong>{value}</strong></div></div>)}</div>;
}
