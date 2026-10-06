import { useEffect, useRef } from 'react';
import { ArrowUpRight, X } from 'lucide-react';
import ScanningPlant from './ScanningPlant';

export default function DemoDialog({ onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    const close = () => onClose();
    dialog.addEventListener('close', close);
    return () => { dialog.removeEventListener('close', close); dialog.close(); };
  }, [onClose]);
  return <dialog ref={ref} className="landing-demo-dialog" aria-labelledby="demo-title"
    onClick={event => { if (event.target === event.currentTarget) ref.current.close(); }}>
    <div className="demo-header"><div><span className="landing-eyebrow">An interactive preview</span><h2 id="demo-title">See your plants differently.</h2></div>
      <button autoFocus className="demo-close" aria-label="Close demo" onClick={() => ref.current.close()}><X size={22} /></button></div>
    <ScanningPlant compact />
    <div className="demo-footer"><p>Illustrative readings show how sensing becomes insight.<br />Explore the working dashboard for a hands-on demo.</p><a href="#/dashboard" className="landing-button">Open dashboard <ArrowUpRight size={17} /></a></div>
  </dialog>;
}
