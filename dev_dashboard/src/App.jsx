import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { SupplyPulseProvider } from './context/SupplyPulseContext';
import TopBar from './components/layout/TopBar';
import FloatingMenu from './components/layout/FloatingMenu';
import CustomCursor from './components/ui/CustomCursor';
import { initSmoothScroll, scrollToTop } from './lib/smoothScroll';
import Landing from './landing/Landing';

import Overview from './pages/Overview';
import PipelinePage from './pages/Pipeline';
import Events from './pages/Events';
import Trace from './pages/Trace';
import StatePage from './pages/State';
import Logs from './pages/Logs';
import Telemetry from './pages/Telemetry';
import Explainability from './pages/Explainability';
import Evaluation from './pages/Evaluation';
import Reference from './pages/Reference';

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<Overview />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/events" element={<Events />} />
        <Route path="/trace" element={<Trace />} />
        <Route path="/state" element={<StatePage />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/telemetry" element={<Telemetry />} />
        <Route path="/explainability" element={<Explainability />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/reference" element={<Reference />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </AnimatePresence>
  );
}

function AppShell() {
  const location = useLocation();
  const isLanding = location.pathname === '/';

  useEffect(() => {
    initSmoothScroll();
  }, []);

  useEffect(() => {
    scrollToTop(true);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-[#060608] text-white flex flex-col selection:bg-rose-500/30 selection:text-white">
      <CustomCursor />
      <FloatingMenu />
      {!isLanding && <TopBar />}
      <main className="flex-1 w-full">
        <AnimatedRoutes />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <SupplyPulseProvider>
        <AppShell />
      </SupplyPulseProvider>
    </BrowserRouter>
  );
}
