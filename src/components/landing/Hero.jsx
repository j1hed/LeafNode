import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, Play } from 'lucide-react';
import { heroBenefits } from '../../data/features';
import ScanningPlant from './ScanningPlant';

export default function Hero({ onDemo }) {
  const reduced = useReducedMotion();
  return <section className="landing-hero landing-container" id="home">
    <motion.div className="hero-copy" initial={reduced ? false : { opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }} transition={{ duration: .75, ease: [.22, 1, .36, 1] }}>
      <span className="landing-eyebrow"><i />A little insight. A lot of growth.</span>
      <h1>Closer to nature.<br /><span>Smarter by<br />LeafNode.</span></h1>
      <p className="hero-description">Know what your plants need, the moment they need it. Smart sensors and local AI turn everyday readings into healthier, happier growth.</p>
      <div className="hero-actions">
        <a className="landing-button" href="#system">Discover LeafNode <ArrowRight size={18} /></a>
        <button className="landing-button landing-button-secondary" onClick={onDemo}><span className="play-icon"><Play size={13} fill="currentColor" /></span>Try the demo</button>
      </div>
      <div className="hero-benefits">
        {heroBenefits.map(({ icon: Icon, title, detail }) => <div key={title}>
          <Icon size={23} strokeWidth={1.6} aria-hidden="true" /><strong>{title}</strong><span>{detail}</span>
        </div>)}
      </div>
    </motion.div>
    <motion.div className="hero-art" initial={reduced ? false : { opacity: 0, x: 25 }}
      animate={{ opacity: 1, x: 0 }} transition={{ duration: 1, ease: 'easeOut' }}>
      <div className="hero-preview-label"><span><i />PLANT INTELLIGENCE</span><span>EXAMPLE READINGS</span></div>
      <ScanningPlant />
    </motion.div>
  </section>;
}
