import { lazy, Suspense, useEffect, useState } from 'react';
import LandingPage from './LandingPage';
import AuthPage from './AuthPage';
import { api, getAccessToken, onAuthChange } from '../services/api';

const DashboardApp = lazy(() => import('./App'));
const isDashboardRoute = () => window.location.hash.startsWith('#/dashboard');

export default function Root() {
  const [dashboard, setDashboard] = useState(isDashboardRoute);
  const [authenticated, setAuthenticated] = useState(Boolean(getAccessToken()));
  const [checkingSession, setCheckingSession] = useState(isDashboardRoute() && Boolean(getAccessToken()));
  useEffect(() => {
    const onHashChange = () => setDashboard(isDashboardRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  useEffect(() => {
    const unsubscribe = onAuthChange(() => setAuthenticated(Boolean(getAccessToken())));
    return unsubscribe;
  }, []);
  useEffect(() => {
    if (!dashboard || !getAccessToken()) { setCheckingSession(false); return; }
    let active = true;
    void api.me().catch(() => undefined).finally(() => { if (active) setCheckingSession(false); });
    return () => { active = false; };
  }, [dashboard]);
  useEffect(() => {
    document.documentElement.dataset.page = dashboard && authenticated ? 'dashboard' : dashboard ? 'auth' : 'landing';
    const light = document.documentElement.dataset.theme === 'light';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dashboard ? (light ? '#f6f5ee' : '#09110f') : '#F7F6EE');
    document.title = dashboard && authenticated ? 'LeafNode — Greenhouse Dashboard' : dashboard ? 'LeafNode — Sign in' : 'LeafNode — Intelligent Plant Monitoring';
    if (dashboard || !window.location.hash || window.location.hash === '#home') window.scrollTo(0, 0);
  }, [dashboard, authenticated]);
  if (!dashboard) return <LandingPage />;
  if (checkingSession) return <div className="dashboard-loading">Checking your growing space…</div>;
  return authenticated
    ? <Suspense fallback={<div className="dashboard-loading">Opening your growing space…</div>}><DashboardApp /></Suspense>
    : <AuthPage onAuthenticated={() => { window.location.hash = '#/dashboard'; setAuthenticated(true); }} />;
}
