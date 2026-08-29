import React, { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ProcessPipeline } from './components/ProcessPipeline';
import { UploadSection } from './components/UploadSection';
import { ChainOfCustody } from './components/ChainOfCustody';
import { ArchitectureSection } from './components/ArchitectureSection';
import { Footer } from './components/Footer';
import { ProcessingModal, PipelineState } from './components/ProcessingModal';
import { ActivityLogModal } from './components/ActivityLogModal';
import { SupabaseAuthModal } from './components/SupabaseAuthModal';
import { ComplianceModal } from './components/ComplianceModal';
import { AnalysesView } from './components/AnalysesView';
import { LibraryView } from './components/LibraryView';
import { AuthGate } from './components/AuthGate';
import { supabase, isSupabaseConfigured } from './lib/supabase';
import { api, CaseSummary, EvidenceSummary, ForensicEvent } from './api/client';
import { EvidenceFile, SupabaseUser } from './types';

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '—';
  if (bytes > 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function toEvidenceFile(e: EvidenceSummary): EvidenceFile {
  const totalBytes = e.recordings.reduce((sum, r) => sum + (r.file_size || 0), 0);
  const status: EvidenceFile['status'] =
    e.status === 'verified' ? 'verified' : e.status === 'tampered' ? 'error' : 'processing';
  return {
    id: e.id,
    name: e.original_filename,
    caseId: e.case_id,
    size: formatBytes(totalBytes),
    uploadedAt: e.acquired_at,
    hash: e.sha256 || '',
    status,
  };
}

const EMPTY_PIPELINE: PipelineState = { phase: 1, progress: 0, logs: [], isCompleted: false, error: null };

export default function App() {
  // ---- auth --------------------------------------------------------------
  const [session, setSession] = useState<Session | null | undefined>(undefined); // undefined = not checked yet
  const currentUser: SupabaseUser | null = session?.user
    ? {
        id: session.user.id,
        email: session.user.email || '',
        role: 'Investigator',
        enterpriseId: session.user.id.slice(0, 8).toUpperCase(),
        name: session.user.email?.split('@')[0] || 'User',
        isLoggedIn: true,
      }
    : null;

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) {
      setSession(null);
      return;
    }
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

  // ---- case / evidence / event data --------------------------------------
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [recentFiles, setRecentFiles] = useState<EvidenceFile[]>([]);
  const [events, setEvents] = useState<ForensicEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  useEffect(() => {
    if (!currentUser) return;
    api
      .listCases()
      .then((list) => {
        setCases(list);
        if (list.length > 0) setActiveCaseId((prev) => prev ?? list[0].id);
      })
      .catch((err) => console.error('Failed to load cases', err));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.id]);

  useEffect(() => {
    if (!activeCaseId) return;
    setEventsLoading(true);
    Promise.all([api.listEvidence(activeCaseId), api.getCaseEvents(activeCaseId)])
      .then(([evidenceList, eventList]) => {
        setRecentFiles(evidenceList.map(toEvidenceFile));
        setEvents(eventList);
      })
      .catch((err) => console.error('Failed to load case data', err))
      .finally(() => setEventsLoading(false));
  }, [activeCaseId]);

  const activeCase = cases.find((c) => c.id === activeCaseId) || null;

  // ---- pipeline (upload -> parse -> extract -> analyze) ------------------
  const [isProcessingOpen, setIsProcessingOpen] = useState(false);
  const [isPipelineBusy, setIsPipelineBusy] = useState(false);
  const [pipelineState, setPipelineState] = useState<PipelineState>(EMPTY_PIPELINE);
  const [pipelineFileName, setPipelineFileName] = useState('');
  const [pipelineCaseName, setPipelineCaseName] = useState('');

  const appendLog = (line: string) =>
    setPipelineState((prev) => ({ ...prev, logs: [...prev.logs, line] }));
  const setPhaseProgress = (phase: PipelineState['phase'], progress: number) =>
    setPipelineState((prev) => ({ ...prev, phase, progress }));

  const handleBeginProcessing = async ({ caseName, file }: { caseName: string; file: File }) => {
    setPipelineState({ ...EMPTY_PIPELINE, logs: [`Uploading ${file.name}…`] });
    setPipelineFileName(file.name);
    setPipelineCaseName(caseName);
    setIsProcessingOpen(true);
    setIsPipelineBusy(true);

    try {
      let targetCase = cases.find((c) => c.name === caseName) || null;
      if (!targetCase) {
        targetCase = await api.createCase(caseName);
        setCases((prev) => [targetCase as CaseSummary, ...prev]);
      }
      setActiveCaseId(targetCase.id);

      const evidence = await api.uploadEvidence(targetCase.id, file);
      appendLog(`Uploaded & sealed. SHA-256: ${evidence.sha256}`);
      setPhaseProgress(1, 25);

      const parsed = await api.parseEvidence(evidence.id);
      appendLog(`Parsed: ${parsed.recordings.length} recording(s) found (vendor: ${parsed.vendor ?? 'unknown'}).`);
      if (parsed.parse_warnings.length) parsed.parse_warnings.forEach((w) => appendLog(`⚠ ${w}`));
      setPhaseProgress(2, 50);

      const extracted = await api.extractEvidence(evidence.id);
      const recovered = extracted.recordings.filter((r) => r.extracted_path).length;
      appendLog(`Extracted: ${recovered}/${extracted.recordings.length} recording(s) recovered.`);
      setPhaseProgress(3, 75);

      const analyzed = await api.analyzeEvidence(evidence.id);
      appendLog(`Analyzed: ${analyzed.events.length} event(s) detected.`);
      analyzed.errors.forEach((e) => appendLog(`⚠ ${e.recording_id}: ${e.error}`));
      setPipelineState((prev) => ({ ...prev, phase: 4, progress: 100, isCompleted: true }));

      const [freshEvidence, freshEvents] = await Promise.all([
        api.listEvidence(targetCase.id),
        api.getCaseEvents(targetCase.id),
      ]);
      setRecentFiles(freshEvidence.map(toEvidenceFile));
      setEvents(freshEvents);
      setCurrentStepId(8);
    } catch (err) {
      setPipelineState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Pipeline failed',
      }));
    } finally {
      setIsPipelineBusy(false);
    }
  };

  // ---- render --------------------------------------------------------------

  if (session === undefined) {
    return <div className="min-h-screen bg-[#f4eee3]" />;
  }

  if (!currentUser) {
    return <AuthGate onAuthenticated={() => {}} />;
  }

  return (
    <div className="min-h-screen bg-[#faf8f5] text-[#142e2e] flex flex-row font-['DM_Sans',sans-serif]">
      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        activeNav={activeNav}
        onNavChange={(nav) => setActiveNav(nav)}
        user={currentUser}
        onOpenProfile={() => setIsAuthModalOpen(true)}
        onLogout={() => setIsAuthModalOpen(true)}
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
                  <UploadSection onBeginProcessing={handleBeginProcessing} busy={isPipelineBusy} />
                </div>
                <div className="lg:col-span-4 flex">
                  <ChainOfCustody recentFiles={recentFiles} onOpenActivityLog={() => setIsActivityLogOpen(true)} />
                </div>
              </div>

              <ArchitectureSection isHighlighted={isArchitectureHighlighted} />
            </div>
          )}

          {activeNav === 'Analyses' && (
            <AnalysesView caseName={activeCase?.name ?? '—'} events={events} loading={eventsLoading} />
          )}

          {activeNav === 'Library' && (
            <LibraryView files={recentFiles} onOpenActivityLog={() => setIsActivityLogOpen(true)} />
          )}
        </main>

        <Footer onOpenCompliance={(tab) => setComplianceModalTab(tab)} />
      </div>

      <ProcessingModal
        isOpen={isProcessingOpen}
        onClose={() => setIsProcessingOpen(false)}
        caseName={pipelineCaseName}
        fileName={pipelineFileName}
        state={pipelineState}
        onReviewTimeline={() => {
          setIsProcessingOpen(false);
          setActiveNav('Analyses');
        }}
      />

      <ActivityLogModal isOpen={isActivityLogOpen} onClose={() => setIsActivityLogOpen(false)} />

      <SupabaseAuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} currentUser={currentUser} />

      <ComplianceModal
        isOpen={complianceModalTab !== null}
        initialTab={complianceModalTab || 'security'}
        onClose={() => setComplianceModalTab(null)}
      />
    </div>
  );
}