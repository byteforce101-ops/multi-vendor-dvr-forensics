import React, { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ProcessPipeline } from './components/ProcessPipeline';
import { UploadSection } from './components/UploadSection';
import { ChainOfCustody } from './components/ChainOfCustody';
import { ArchitectureSection } from './components/ArchitectureSection';
import { Footer } from './components/Footer';
import { ProcessingModal } from './components/ProcessingModal';
import { ActivityLogModal } from './components/ActivityLogModal';
import { AuthModal } from './components/AuthModal';
import { ComplianceModal } from './components/ComplianceModal';
import { AnalysesView } from './components/AnalysesView';
import { LibraryView } from './components/LibraryView';
import { supabase, isSupabaseConfigured, DEFAULT_USER } from './lib/supabase';
import { EvidenceFile, SupabaseUser, VideoAnalysisResult } from './types';

export default function App() {
  // ---- auth (real Supabase session; UI stays visible either way) --------
  const [session, setSession] = useState<Session | null>(null);
  const isAuthenticated = !!session;
  const currentUser: SupabaseUser = session?.user
    ? {
        id: session.user.id,
        email: session.user.email || '',
        role: 'Investigator',
        enterpriseId: session.user.id.slice(0, 8).toUpperCase(),
        name: session.user.email?.split('@')[0] || 'User',
        isLoggedIn: true,
      }
    : { ...DEFAULT_USER, isLoggedIn: false };

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) return;
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, sess) => setSession(sess));
    return () => sub.subscription.unsubscribe();
  }, []);

  // ---- navigation / layout -------------------------------------------------
  const [activeNav, setActiveNav] = useState<'Pipelines' | 'Analyses' | 'Library'>('Pipelines');
  const [currentStepId, setCurrentStepId] = useState<number>(3);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [isActivityLogOpen, setIsActivityLogOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [complianceModalTab, setComplianceModalTab] = useState<'security' | 'compliance' | 'api' | null>(null);
  const [isArchitectureHighlighted, setIsArchitectureHighlighted] = useState(false);

  useEffect(() => {
    const handleResize = () => setIsSidebarOpen(window.innerWidth >= 1024);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleNavigateToArchitecture = () => {
    setActiveNav('Pipelines');
    setTimeout(() => {
      const el = document.getElementById('architecture-overview');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setIsArchitectureHighlighted(true);
        setTimeout(() => setIsArchitectureHighlighted(false), 3500);
      }
    }, 100);
  };

  // ---- evidence + processing (client-side only, no case DB) -------------
  const [recentFiles, setRecentFiles] = useState<EvidenceFile[]>([]);
  const [processingData, setProcessingData] = useState<{ caseName: string; evidenceId: string; file: EvidenceFile | null }>({
    caseName: '',
    evidenceId: '',
    file: null,
  });
  const [isProcessingOpen, setIsProcessingOpen] = useState(false);
  const [analysis, setAnalysis] = useState<VideoAnalysisResult | null>(null);

  const handleFileUploaded = (file: EvidenceFile) => {
    setRecentFiles((prev) => [file, ...prev]);
  };

  const handleBeginProcessing = (data: { caseName: string; evidenceId: string; file: EvidenceFile | null }) => {
    setProcessingData(data);
    setIsProcessingOpen(true);
  };

  const handleLogout = async () => {
    if (session) {
      if (supabase) await supabase.auth.signOut();
    } else {
      setIsAuthModalOpen(true);
    }
  };

  return (
    <div className="min-h-screen bg-[#faf8f5] text-[#142e2e] flex flex-row font-['DM_Sans',sans-serif]">
      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        activeNav={activeNav}
        onNavChange={(nav) => setActiveNav(nav)}
        user={currentUser}
        onOpenProfile={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
        onOpenActivityLog={() => setIsActivityLogOpen(true)}
        onOpenCompliance={(tab) => setComplianceModalTab(tab)}
        onNavigateToArchitecture={handleNavigateToArchitecture}
      />

      <div className="flex-1 flex flex-col min-w-0 transition-all">
        <Header
          user={currentUser}
          onNavChange={(nav) => setActiveNav(nav as any)}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onOpenActivityLog={() => setIsActivityLogOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          sidebarOpen={isSidebarOpen}
          onNavigateToArchitecture={handleNavigateToArchitecture}
        />

        <main className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 pt-7 pb-12 flex-1">
          {activeNav === 'Pipelines' && (
            <div className="space-y-6 sm:space-y-7">
              <ProcessPipeline currentStepId={currentStepId} />

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-7 items-stretch">
                <div className="lg:col-span-8 flex">
                  <UploadSection
                    onBeginProcessing={handleBeginProcessing}
                    onFileUploaded={handleFileUploaded}
                    isAuthenticated={isAuthenticated}
                    onRequestLogin={() => setIsAuthModalOpen(true)}
                  />
                </div>
                <div className="lg:col-span-4 flex">
                  <ChainOfCustody recentFiles={recentFiles} onOpenActivityLog={() => setIsActivityLogOpen(true)} />
                </div>
              </div>

              <ArchitectureSection isHighlighted={isArchitectureHighlighted} />
            </div>
          )}

          {activeNav === 'Analyses' && <AnalysesView analysis={analysis} />}

          {activeNav === 'Library' && (
            <LibraryView files={recentFiles} onOpenActivityLog={() => setIsActivityLogOpen(true)} />
          )}
        </main>

        <Footer onOpenCompliance={(tab) => setComplianceModalTab(tab)} />
      </div>

      <ProcessingModal
        isOpen={isProcessingOpen}
        onClose={() => setIsProcessingOpen(false)}
        caseName={processingData.caseName}
        evidenceId={processingData.evidenceId}
        file={processingData.file}
        onCompleteStep={(stepId) => {
          setCurrentStepId(stepId);
          setActiveNav('Analyses');
        }}
        onAnalysisComplete={(result) => setAnalysis(result)}
      />

      <ActivityLogModal isOpen={isActivityLogOpen} onClose={() => setIsActivityLogOpen(false)} />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        isAuthenticated={isAuthenticated}
        userEmail={currentUser.email}
      />

      <ComplianceModal
        isOpen={complianceModalTab !== null}
        initialTab={complianceModalTab || 'security'}
        onClose={() => setComplianceModalTab(null)}
      />
    </div>
  );
}