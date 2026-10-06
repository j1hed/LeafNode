import { Activity, BrainCircuit, Droplets, Eye, Leaf, Radio, ShieldCheck, SlidersHorizontal, Sprout, Sun, Thermometer, Waves, FlaskConical, TrendingUp, Zap } from 'lucide-react';

export const navigation = [
  { label: 'Home', href: '#home' }, { label: 'About', href: '#about' },
  { label: 'Features', href: '#features' }, { label: 'System', href: '#system' },
  { label: 'Gallery', href: '#gallery' }, { label: 'Contact', href: '#contact' },
];
export const heroBenefits = [
  { icon: Sprout, title: 'Healthier Plants', detail: 'Early disease detection' },
  { icon: BrainCircuit, title: 'Smarter Decisions', detail: 'AI-powered insights' },
  { icon: Leaf, title: 'Sustainable Future', detail: 'Efficient resource use' },
];
export const processSteps = [
  { icon: Radio, title: 'Sense', detail: 'Collect real-time environmental data' },
  { icon: Eye, title: 'Analyze', detail: 'Detect plant condition with Edge AI' },
  { icon: BrainCircuit, title: 'Decide', detail: 'Generate intelligent actions' },
  { icon: Zap, title: 'Act', detail: 'Control actuators automatically' },
  { icon: SlidersHorizontal, title: 'Supervise', detail: 'Monitor, alert and stay in control' },
];
export const growthBenefits = [
  { icon: Activity, title: 'Real-time Monitoring' },
  { icon: Eye, title: 'AI-powered Detection' },
  { icon: SlidersHorizontal, title: 'Automated Control' },
  { icon: ShieldCheck, title: 'Local & Secure Operation' },
];
export const impactItems = [
  { icon: Droplets, title: 'Save Water', detail: "Use only what's needed", number: '01' },
  { icon: Sprout, title: 'Healthier Crops', detail: 'Early problem detection', number: '02' },
  { icon: TrendingUp, title: 'Higher Productivity', detail: 'Data-driven decisions', number: '03' },
];
export const sensorMetrics = [
  { icon: Thermometer, value: '24°C', label: 'Temperature', position: 'temperature', delay: 1.2 },
  { icon: Droplets, value: '68%', label: 'Humidity', position: 'humidity', delay: 1.6 },
  { icon: Sun, value: '800 lux', label: 'Light', position: 'light', delay: 2 },
  { icon: Leaf, value: '42%', label: 'Soil Moisture', position: 'soil', delay: 2.4 },
  { icon: FlaskConical, value: 'pH 6.5', label: 'Soil pH', position: 'ph', delay: 2.8 },
  { icon: Waves, value: '75%', label: 'Water Level', position: 'water', delay: 3.1 },
];
export const images = {
  plant: '/assets/landing/plant.png',
  scanning: '/assets/landing/plant-scanning.png',
  dashboard: '/assets/landing/dashboard-showcase.png',
  device: '/assets/landing/greenhouse-device.png',
};
const externalUrl = value => /^https?:\/\//.test(value || '') ? value : '';
export const contact = {
  email: import.meta.env.VITE_CONTACT_EMAIL || '',
  socials: [
    { label: 'LinkedIn', url: externalUrl(import.meta.env.VITE_LINKEDIN_URL) },
    { label: 'GitHub', url: externalUrl(import.meta.env.VITE_GITHUB_URL) },
    { label: 'YouTube', url: externalUrl(import.meta.env.VITE_YOUTUBE_URL) },
  ],
};
