import Panel from './Panel';
import TelemetryChart from './TelemetryChart';
import { useDashboard } from '../app/DashboardContext';
import { series } from '../services/data';
import { ResourceState } from './ApiState';
export default function TrendsPanel() {
  const { sensors } = useDashboard();
  const sensorData = sensors.data;
  return <Panel title="Sensor Trends" className="trends-panel" action={<span className="chart-range">Latest 100 records</span>}>
    <ResourceState resource={sensors} empty={!sensorData?.data.length} message="No sensor history available."/>
    {sensorData && ['temperature', 'soil', 'humidity'].map((field, index) => {
      const points = series(sensorData.data, field);
      return <TelemetryChart key={field} label={['Temperature (°C)', 'Soil Moisture (%)', 'Air Humidity (%)'][index]}
        values={points.map(point => point.value)} color={['var(--leaf-green)', 'var(--orange)', 'var(--cyan)'][index]}
        current={points.length ? String(points[points.length - 1].value) : '—'} labels={points.filter((_, i) => i === 0 || i === points.length - 1).map(point => point.label)} showTime/>;
    })}
  </Panel>;
}
