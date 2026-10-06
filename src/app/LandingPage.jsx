import { useCallback, useState } from 'react';
import { MotionConfig } from 'framer-motion';
import Navbar from '../components/landing/Navbar';
import Hero from '../components/landing/Hero';
import HowItWorks from '../components/landing/HowItWorks';
import DashboardShowcase from '../components/landing/DashboardShowcase';
import SmarterGrowth from '../components/landing/SmarterGrowth';
import Impact from '../components/landing/Impact';
import Footer from '../components/landing/Footer';
import DemoDialog from '../components/landing/DemoDialog';

export default function LandingPage() {
  const [demoOpen, setDemoOpen] = useState(false);
  const closeDemo = useCallback(() => setDemoOpen(false), []);
  return <MotionConfig reducedMotion="user"><div className="landing-page">
    <a className="landing-skip-link" href="#main">Skip to content</a>
    <Navbar />
    <main id="main">
      <Hero onDemo={() => setDemoOpen(true)} />
      <HowItWorks />
      <DashboardShowcase />
      <SmarterGrowth />
      <Impact />
    </main>
    <Footer />
    {demoOpen && <DemoDialog onClose={closeDemo} />}
  </div></MotionConfig>;
}
