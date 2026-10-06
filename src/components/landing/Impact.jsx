import { impactItems } from '../../data/features';
import Reveal from './Reveal';

export default function Impact() {
  return <section className="landing-section impact-section">
    <div className="landing-container">
      <Reveal className="section-intro centered">
        <span className="landing-eyebrow">Built for a sustainable tomorrow</span>
        <h2>Smart Agriculture. Real Impact.</h2>
        <p>LeafNode contributes to more efficient resource use, healthier crop quality and a more sustainable agricultural future.</p>
      </Reveal>
      <div className="impact-grid">{impactItems.map(({ icon: Icon, title, detail, number }, index) => <Reveal key={title} delay={index * .08}>
        <article className="impact-card"><span className="impact-number">{number}</span><Icon size={35} strokeWidth={1.4} /><h3>{title}</h3><p>{detail}</p></article>
      </Reveal>)}</div>
    </div>
  </section>;
}
