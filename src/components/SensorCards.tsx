import { useDashboard } from '../app/DashboardContext';
import { reading, series } from '../services/data';
import MetricCard from './MetricCard';
import { ResourceState } from './ApiState';

const metrics = [
  { key: 'temperature', label: 'Temperature', unit: '°C', icon: '21_temperature.png', color: 'green' },
  { key: 'humidity', label: 'Air Humidity', unit: '%', icon: '22_air_humidity.png', color: 'cyan' },
  { key: 'soil', label: 'Soil Moisture', unit: '%', icon: '23_soil_moisture.png', color: 'orange' },
  { key: 'light', label: 'Light Level', unit: '', icon: '24_light_level.png', color: 'yellow' },
  { key: 'ph', label: 'Soil pH', unit: '', icon: '23_soil_moisture.png', color: 'green' },
  { key: 'pressure', label: 'Pressure', unit: '', icon: '21_temperature.png', color: 'cyan' },
  { key: 'gas', label: 'Gas', unit: '', icon: '22_air_humidity.png', color: 'orange' },
];
export default function SensorCards({ trends = false }: { trends?: boolean }) {
  const { latest, sensors } = useDashboard();
  return <><ResourceState resource={latest} empty={!latest.data?.esp32} message="Waiting for ESP32 sensor readings."/>
    <div className={trends ? 'workspace-metrics' : 'metrics-grid'}>{metrics.map(metric => {
      const value = reading(latest.data?.esp32?.[metric.key]);
      return <MetricCard key={metric.key} label={metric.label} value={value === null ? '—' : String(value)} unit={value === null ? '' : metric.unit}
        icon={'/assets/icons/03_sensors_analytics/' + metric.icon} color={'var(--metric-' + metric.color + ')'}
        values={series(sensors.data?.data ?? [], metric.key).map(point => point.value)} showTrend={trends}/>;
    })}</div></>;
}
