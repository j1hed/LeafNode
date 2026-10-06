import { ArrowRight } from 'lucide-react';
import { processSteps } from '../../data/features';
import Reveal from './Reveal';

export default function HowItWorks() {
  return <section className="landing-section how-section" id="about">
    <div className="landing-container">
      <Reveal className="section-intro centered">
        <span className="landing-eyebrow">How it works</span>
        <h2>From Sensing to Action</h2>
        <p>LeafNode integrates environmental sensing, computer vision and intelligent control in a complete local system. Data is collected, analyzed and transformed into real actions to keep plants healthy.</p>
      </Reveal>
      <ol className="process-steps" id="system">
        {processSteps.map(({ icon: Icon, title, detail }, index) => <li key={title}>
          <Reveal delay={index * .07}>
            <div className="process-icon"><Icon size={28} strokeWidth={1.45} /><span>0{index + 1}</span></div>
            <h3>{title}</h3><p>{detail}</p>
          </Reveal>
          {index < processSteps.length - 1 && <ArrowRight className="process-arrow" size={20} strokeWidth={1.3} aria-hidden="true" />}
        </li>)}
      </ol>
    </div>
  </section>;
}
