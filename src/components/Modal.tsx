import type { ReactNode } from 'react';
import { X } from 'lucide-react';

export default function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return <div className="modal-backdrop" onMouseDown={onClose}><div className="modal-card" onMouseDown={e => e.stopPropagation()}><header><h3>{title}</h3><button onClick={onClose} aria-label="Close modal"><X size={16} /></button></header><div className="modal-content">{children}</div></div></div>;
}
