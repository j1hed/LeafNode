export type SensorState = {
  temperature: number;
  airHumidity: number;
  soilMoisture: number;
  lightLevel: number;
  waterTankLevel: number;
};

export type ActuatorState = {
  irrigationPump: boolean;
  coolingFan: boolean;
  solenoidValve: boolean;
  growLight: boolean;
  peltierCooling: boolean;
  relays: boolean;
};

export type HistoryRow = {
  time: string;
  type: 'Alert' | 'Action' | 'Decision' | 'Anomaly' | 'Sensor' | 'System';
  source: string;
  description: string;
};

export type DashboardData = {
  system: {
    online: boolean;
    mode: string;
    jetson: string;
    esp32_1: string;
    esp32_2: string;
    communication: string;
    date: string;
    time: string;
  };
  sensors: SensorState;
  camera: {
    state: string;
    confidence: number;
    disease: string;
  };
  actuators: ActuatorState;
  recommendation: {
    product: string;
    confidence: number;
    validation: string;
  };
  jetson: {
    utilization: number;
    cpuTemperature: number;
  };
};
