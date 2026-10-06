import { ArrowRight, ArrowUpRight, Mail } from 'lucide-react';
import Brand from './Brand';
import { contact, navigation } from '../../data/features';

export default function Footer() {
  return <footer className="landing-footer" id="contact">
    <div className="landing-container">
      <div className="footer-invitation">
        <div><span className="landing-eyebrow">The future grows here</span><h2>Let's grow something better.</h2></div>
        <a href="#/dashboard" className="landing-button">Get Started <ArrowRight size={18} /></a>
      </div>
      <div className="footer-main">
        <div><Brand /><p>Smart IoT &amp; Edge AI Platform</p>{contact.email && <a className="footer-email" href={'mailto:' + contact.email}><Mail size={16} />{contact.email}</a>}</div>
        <nav aria-label="Footer navigation">{navigation.filter(item => item.label !== 'Gallery').map(item => <a href={item.href} key={item.label}>{item.label}</a>)}</nav>
        <div className="footer-socials">{contact.socials.map(item => item.url
          ? <a href={item.url} target="_blank" rel="noopener noreferrer" key={item.label}>{item.label}<ArrowUpRight size={14} /></a>
          : <span className="social-unavailable" title="Official link will be announced" key={item.label}>{item.label}</span>)}</div>
      </div>
      <div className="footer-bottom"><span>© 2026 LeafNode. All rights reserved.</span><span>Smarter Plants. A Greener Tomorrow.</span></div>
    </div>
  </footer>;
}
