import { useDashboard } from '../app/DashboardContext';
export default function BottomStatusBar() {
  const { synced, latest } = useDashboard();
  return <footer className="bottom-status">
    <div className="bottom-segment"><span>Refresh: <strong>1 second after each completed update</strong></span></div>
    <div className="bottom-segment"><span>Last complete sync: <strong>{synced ?? 'Not yet synchronized'}</strong></span></div>
    <div className="bottom-segment"><span>Detection: <strong>{latest.data?.jetson ? 'Available' : 'Unavailable'}</strong></span></div>
  </footer>;
}
