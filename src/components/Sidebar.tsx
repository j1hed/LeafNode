import { ChevronLeft, ChevronRight } from 'lucide-react';
import IconImage from './IconImage';
import ThemeToggle from './ThemeToggle';

export type ViewName = 'Dashboard' | 'Sensors' | 'AI Agents' | 'Camera Analysis' | 'Actuators' | 'Recommendations' | 'History' | 'Alerts' | 'Settings';

type Props = {
  active: ViewName;
  onNavigate: (view: ViewName) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onLogout: () => void;
};

const nav: Array<{ label: ViewName; icon: string }> = [
  { label: 'Dashboard', icon: '/assets/icons/01_navigation_brand/02_dashboard_grid.png' },
  { label: 'Sensors', icon: '/assets/icons/01_navigation_brand/03_sensors_thermometer.png' },
  { label: 'AI Agents', icon: '/assets/icons/01_navigation_brand/04_ai_agents_brain.png' },
  { label: 'Camera Analysis', icon: '/assets/icons/01_navigation_brand/05_camera_analysis.png' },
  { label: 'Actuators', icon: '/assets/icons/01_navigation_brand/06_actuators_gear.png' },
  { label: 'Recommendations', icon: '/assets/icons/01_navigation_brand/07_recommendations_leaf.png' },
  { label: 'History', icon: '/assets/icons/01_navigation_brand/08_history_clock.png' },
  { label: 'Alerts', icon: '/assets/icons/01_navigation_brand/09_alerts_warning.png' },
  { label: 'Settings', icon: '/assets/icons/01_navigation_brand/10_settings_gear.png' },
];

export default function Sidebar({ active, onNavigate, collapsed, onToggleCollapse, onLogout }: Props) {
  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <button className="sidebar-collapse" onClick={onToggleCollapse} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
      <a className="brand-block" href="#home" aria-label="LeafNode home">
        <IconImage src="/assets/icons/01_navigation_brand/01_leafnode_logo.png" className="brand-logo" alt="LeafNode logo" />
        <div><div className="brand-title">LeafNode</div><div className="brand-subtitle">Your connected<br />growing space</div></div>
      </a>
      <div className="nav-caption">WORKSPACE</div>
      <nav className="side-nav" aria-label="LeafNode navigation">
        {nav.map((item) => (
          <button key={item.label} className={`nav-item ${active === item.label ? 'active' : ''}`} onClick={() => onNavigate(item.label)} title={item.label} aria-label={item.label} aria-current={active === item.label ? 'page' : undefined}>
            <IconImage src={item.icon} className="nav-icon" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-theme"><ThemeToggle /></div>
      <button className="sidebar-logout" onClick={onLogout}>Log out</button>
      <div className="sidebar-art">
        <IconImage src="/assets/icons/01_navigation_brand/12_smart_plant_circuit.png" className="plant-circuit" alt="Plant circuit illustration" />
        {!collapsed && <div className="sidebar-art-copy"><strong>LeafNode Edge</strong><span>Local intelligence • Autonomous control</span></div>}
      </div>
    </aside>
  );
}
