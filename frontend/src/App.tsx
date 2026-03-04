import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { HomePage } from './pages/HomePage';
import { MetaPage } from './pages/MetaPage';
import { JobPage } from './pages/JobPage';
import { PatchNotePage } from './pages/PatchNotePage';
import { VersionContext, useVersionState } from './hooks/useVersion';

export default function App() {
  const versionState = useVersionState();

  return (
    <VersionContext.Provider value={versionState}>
      <BrowserRouter>
        <div className="min-h-screen bg-[#0F1117]">
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/meta" element={<MetaPage />} />
              <Route path="/jobs" element={<JobPage />} />
              <Route path="/patch-notes" element={<PatchNotePage />} />
            </Routes>
          </main>
          <footer className="mt-8 border-t border-gray-800 py-4 text-center text-xs text-gray-400">
            Data based on NEXON Open API
          </footer>
        </div>
      </BrowserRouter>
    </VersionContext.Provider>
  );
}
