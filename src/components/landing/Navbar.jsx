import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';
import Brand from './Brand';
import { navigation } from '../../data/features';

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const menuButton = useRef(null);
  useEffect(() => {
    function onKey(event) {
      if (event.key === 'Escape' && open) { setOpen(false); menuButton.current?.focus(); }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);
  return <header className="landing-nav">
    <div className="landing-container landing-nav-inner">
      <Brand />
      <nav id="landing-navigation" className={'landing-nav-links ' + (open ? 'is-open' : '')} aria-label="Main navigation">
        {navigation.map(item => <a href={item.href} key={item.label} onClick={() => setOpen(false)}>{item.label}</a>)}
        <a href="#/dashboard" className="landing-button mobile-start">Get Started <ArrowUpRight size={17} /></a>
      </nav>
      <a href="#/dashboard" className="landing-button nav-start">Get Started <ArrowUpRight size={17} /></a>
      <button ref={menuButton} className="landing-menu-button" type="button" aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open} aria-controls="landing-navigation" onClick={() => setOpen(!open)}>
        {open ? <X size={24} /> : <Menu size={24} />}
      </button>
    </div>
  </header>;
}
