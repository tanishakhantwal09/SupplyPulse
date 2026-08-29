import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { SupplyPulseProvider } from './context/SupplyPulseContext';
import TopBar from './components/layout/TopBar';

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
        <Route path="/" element={<Overview />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/events" element={<Events />} />
        <Route path="/trace" element={<Trace />} />
        <Route path="/state" element={<StatePage />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/telemetry" element={<Telemetry />} />
        <Route path="/explainability" element={<Explainability />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/reference" element={<Reference />} />
        <Route path="*" element={<Overview />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <SupplyPulseProvider>
        <div className="min-h-screen bg-[#060608] text-white flex flex-col selection:bg-rose-500/30 selection:text-white">
          <TopBar />
          <main className="flex-1 w-full">
            <AnimatedRoutes />
          </main>
        </div>
      </SupplyPulseProvider>
    </BrowserRouter>
  );
}
