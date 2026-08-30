import React, { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { UploadSection } from './components/UploadSection';
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
        role: 'Senior Examiner',
        enterpriseId: session.user.id.slice(0, 8).toUpperCase(),
        name: session.user.email?.split('@')[0] || 'Examiner',
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
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isActivityLogOpen, setIsActivityLogOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [complianceModalTab, setComplianceModalTab] = useState<'security' | 'compliance' | 'api' | null>(null);

  // ---- evidence + processing -----------------------------------------------
  const [recentFiles, setRecentFiles] = useState<EvidenceFile[]>([]);
  const [processingData, setProcessingData] = useState<{ caseName: string; evidenceId: string; file: EvidenceFile | null }>({
    caseName: '',
    evidenceId: '',
    file: null,
  });
  const [isProcessingOpen, setIsProcessingOpen] = useState(false);
  const [analysis, setAnalysis] = useState<VideoAnalysisResult | null>(null);
  const [videoBlobUrl, setVideoBlobUrl] = useState<string | undefined>(undefined);

  const handleFileUploaded = (file: EvidenceFile) => {
    setRecentFiles((prev) => [file, ...prev]);
    if (file.sourceFile) {
      setVideoBlobUrl(URL.createObjectURL(file.sourceFile));
    }
  };

  const handleBeginProcessing = (data: { caseName: string; evidenceId: string; file: EvidenceFile | null }) => {
    setProcessingData(data);
    if (data.file?.sourceFile) {
      setVideoBlobUrl(URL.createObjectURL(data.file.sourceFile));
    }
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
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex flex-col font-['Inter',sans-serif]">
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
      />

      <div className="flex-1 flex flex-col min-w-0 transition-all bg-[#F8FAFC]">
        <Header
          user={currentUser}
          onNavChange={(nav) => setActiveNav(nav as any)}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onOpenActivityLog={() => setIsActivityLogOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          sidebarOpen={isSidebarOpen}
        />

        <main className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
          {activeNav === 'Pipelines' && (
            <div className="max-w-4xl mx-auto space-y-6">
              <UploadSection
                onBeginProcessing={handleBeginProcessing}
                onFileUploaded={handleFileUploaded}
                isAuthenticated={isAuthenticated}
                onRequestLogin={() => setIsAuthModalOpen(true)}
              />
            </div>
          )}

          {activeNav === 'Analyses' && <AnalysesView analysis={analysis} videoUrl={videoBlobUrl} />}

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
        onCompleteStep={() => {
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