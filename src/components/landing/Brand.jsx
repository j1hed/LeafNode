import { Leaf } from 'lucide-react';

export default function Brand() {
  return <a className="landing-brand" href="#home" aria-label="LeafNode home">
    <span className="landing-brand-mark"><Leaf size={25} strokeWidth={1.8} /></span>
    <span>Leaf<span className="brand-node">Node</span></span>
  </a>;
}
