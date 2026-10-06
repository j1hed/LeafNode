import type { ReactNode } from 'react';

type Props = {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  icon?: ReactNode;
};

export default function Panel({ title, action, children, className = '', icon }: Props) {
  return (
    <section className={`dashboard-card ${className}`}>
      <header className="panel-header">
        <div className="panel-title-wrap">{icon}<h2 className="panel-title">{title}</h2></div>
        {action && <div className="panel-action">{action}</div>}
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}
