import { ArrowUpRight, CircleCheck } from 'lucide-react';
import { images } from '../../data/features';
import Reveal from './Reveal';

export default function DashboardShowcase() {
  return <section className="landing-section showcase-section" id="gallery">
    <div className="landing-container">
      <Reveal className="showcase-heading">
        <div className="section-intro"><span className="landing-eyebrow">One connected ecosystem</span><h2>Your growing space.<br />All in one place.</h2></div>
        <div className="showcase-description"><p>From a single leaf to the bigger picture. Understand your plants, follow every reading, and stay in control wherever you are.</p><a className="landing-text-link" href="#/dashboard">Explore the dashboard <ArrowUpRight size={19} /></a></div>
      </Reveal>
      <Reveal className="dashboard-showcase">
        {/* The supplied image already includes the desktop and phone mockups. Keep it intact. */}
        <img src={images.dashboard} alt="The supplied LeafNode desktop dashboard and mobile app, showing plant health, environmental readings, and actuator controls"
          width="1448" height="1086" loading="lazy" decoding="async" />
      </Reveal>
      <div className="showcase-assurances">
        {['Built for desktop & mobile', 'Clear insights, wherever you grow', 'You stay in control'].map(text => <span key={text}><CircleCheck size={17} strokeWidth={1.7} />{text}</span>)}
      </div>
    </div>
  </section>;
}
