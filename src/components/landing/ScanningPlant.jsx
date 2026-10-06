import { useRef } from 'react';
import { motion, useInView, useReducedMotion } from 'framer-motion';
import { Leaf } from 'lucide-react';
import { images, sensorMetrics } from '../../data/features';

export default function ScanningPlant({ compact = false }) {
  const ref = useRef(null);
  const reduced = useReducedMotion();
  const visible = useInView(ref, { amount: .15 });
  const reveal = delay => ({
    initial: reduced ? false : { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { delay: reduced ? 0 : delay, duration: reduced ? 0 : .65, ease: 'easeOut' },
  });
  return <div ref={ref} className={'scanning-plant ' + (compact ? 'is-compact' : '')} aria-label="Illustration of a healthy plant with example sensor readings">
    <img className="scanning-plant-image" src={images.plant} alt="A young green plant in rich soil inside a sunlit greenhouse"
      width="1254" height="1254" fetchPriority={compact ? 'auto' : 'high'} />
    <motion.div className="scan-ring" {...reveal(.6)} aria-hidden="true">
      <motion.svg viewBox="0 0 100 100" fill="none"
        animate={visible && !reduced ? { opacity: [.5, .9, .5] } : { opacity: .65 }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}>
        <circle cx="50" cy="50" r="47" stroke="currentColor" strokeWidth=".35" />
        <circle cx="50" cy="50" r="47" stroke="currentColor" strokeWidth=".9" strokeDasharray="8 66" />
      </motion.svg>
    </motion.div>
    <motion.div className="scan-brackets" {...reveal(.8)} aria-hidden="true">
      {[0, 1, 2, 3].map(corner => <motion.i key={corner}
        animate={visible && !reduced ? { y: [0, -2, 0] } : { y: 0 }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }} />)}
    </motion.div>
    {!reduced && visible && <motion.div className="scan-beam" aria-hidden="true" initial={{ opacity: 0 }}
      animate={{ top: ['24%', '76%'], opacity: [0, .5, .5, 0] }}
      transition={{ duration: 5.5, delay: 1, repeat: Infinity, repeatDelay: 2.5, ease: 'easeInOut' }} />}
    {sensorMetrics.map(({ icon: Icon, value, label, position, delay }) => (
      <motion.div className={'scan-metric scan-' + position} key={position} {...reveal(delay)}>
        <Icon size={22} strokeWidth={1.65} aria-hidden="true" />
        <div><strong>{value}</strong><span>{label}</span></div>
      </motion.div>
    ))}
    <motion.div className="scan-health" {...reveal(3.5)}>
      <Leaf size={26} strokeWidth={1.6} aria-hidden="true" />
      <div><strong>Plant detected</strong><span><i />Healthy</span></div>
    </motion.div>
    <span className="scan-caption">A glimpse into intelligent growing</span>
  </div>;
}
