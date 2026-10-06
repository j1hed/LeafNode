import { ArrowRight, Radio } from 'lucide-react';
import { images, growthBenefits } from '../../data/features';
import Reveal from './Reveal';

export default function SmarterGrowth() {
  return <section className="landing-section growth-section" id="features">
    <div className="landing-container growth-layout">
      <Reveal className="growth-art">
        <img className="growth-image" src={images.scanning} width="1254" height="1254" loading="lazy" decoding="async"
          alt="LeafNode plant-scanning reference with temperature, humidity, light, soil moisture, pH, water level, and healthy plant status" />
        <div className="growth-device"><img src={images.device} width="1448" height="1086" loading="lazy" decoding="async" alt="LeafNode sensor monitoring a plant in greenhouse soil" /><span><Radio size={14} />Connected at the roots</span></div>
      </Reveal>
      <Reveal className="growth-copy section-intro" delay={.1}>
        <span className="landing-eyebrow">Rooted in nature. Powered by intelligence.</span>
        <h2>A Smarter<br />Way to Grow</h2>
        <p>Whether in greenhouses, research labs or urban farming, LeafNode helps you understand, protect and grow your plants with the power of IoT and AI.</p>
        <a className="landing-button" href="#contact">Join the Green Future <ArrowRight size={18} /></a>
        <div className="growth-benefits">{growthBenefits.map(({ icon: Icon, title }) => <div key={title}><Icon size={22} strokeWidth={1.5} /><span>{title}</span></div>)}</div>
      </Reveal>
    </div>
  </section>;
}
