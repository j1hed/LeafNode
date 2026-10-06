import type { DashboardData, HistoryRow } from '../types/dashboard';

export const dashboardData: DashboardData = {
  system: {
    online: true,
    mode: 'Auto Mode',
    jetson: 'Connected',
    esp32_1: 'Connected',
    esp32_2: 'Connected',
    communication: 'Bluetooth / UART',
    date: 'May 20, 2025',
    time: '14:32:18',
  },
  sensors: {
    temperature: 28.6,
    airHumidity: 58.4,
    soilMoisture: 22.7,
    lightLevel: 632,
    waterTankLevel: 41.2,
  },
  camera: {
    state: 'Mild Stress',
    confidence: 82,
    disease: 'Early Blight (Alternaria solani)',
  },
  actuators: {
    irrigationPump: true,
    coolingFan: true,
    solenoidValve: true,
    growLight: false,
    peltierCooling: true,
    relays: true,
  },
  recommendation: {
    product: 'Calcium Nitrate',
    confidence: 87,
    validation: 'Required',
  },
  jetson: {
    utilization: 82,
    cpuTemperature: 54.2,
  },
};

export const trends = {
  labels: ['13:32', '13:42', '13:52', '14:02', '14:12', '14:22', '14:32'],
  temperature: [27.9, 28.2, 28.0, 28.4, 28.7, 28.5, 28.6],
  soil: [27.5, 26.4, 25.1, 24.2, 23.5, 23.0, 22.7],
  humidity: [60.5, 59.7, 60.1, 59.2, 58.8, 58.6, 58.4],
};

export const alerts = [
  { title: 'Low Soil Moisture', detail: 'Soil moisture is below threshold (22.7%)', time: '14:31', level: 'danger' as const, icon: '/assets/icons/07_alerts_logs_navigation/54_low_soil_moisture_alert.png' },
  { title: 'High Temperature', detail: 'Temperature exceeds optimal range (28.6°C)', time: '14:28', level: 'danger' as const, icon: '/assets/icons/07_alerts_logs_navigation/55_high_temperature_alert.png' },
  { title: 'Low Water Tank Level', detail: 'Water tank level is low (41.2%)', time: '14:25', level: 'warning' as const, icon: '/assets/icons/07_alerts_logs_navigation/56_low_water_tank_alert.png' },
  { title: 'Communication Warning', detail: 'ESP32 #2 signal weak (RSSI: -82 dBm)', time: '14:21', level: 'warning' as const, icon: '/assets/icons/07_alerts_logs_navigation/57_communication_warning.png' },
];

export const historyRows: HistoryRow[] = [
  { time: '14:31:45', type: 'Alert', source: 'Sensors', description: 'Low soil moisture detected (22.7%)' },
  { time: '14:31:40', type: 'Action', source: 'Action Agent', description: 'Irrigation Pump ON, Valve OPEN' },
  { time: '14:30:12', type: 'Decision', source: 'Decision Agent', description: 'Irrigation recommended (duration: 30s)' },
  { time: '14:29:58', type: 'Anomaly', source: 'Surveillance Agent', description: 'Leaf spots detected (Early Blight)' },
  { time: '14:29:30', type: 'Sensor', source: 'Temperature', description: 'Temperature: 28.6 °C' },
  { time: '14:29:30', type: 'Sensor', source: 'Humidity', description: 'Air Humidity: 58.4 %' },
  { time: '14:29:30', type: 'Sensor', source: 'Soil Moisture', description: 'Soil Moisture: 22.7 %' },
  { time: '14:29:15', type: 'System', source: 'System', description: 'System started in Auto Mode' },
];
