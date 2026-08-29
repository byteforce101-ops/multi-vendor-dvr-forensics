import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ProcessPipeline } from './components/ProcessPipeline';
import { UploadSection } from './components/UploadSection';
import { ChainOfCustody } from './components/ChainOfCustody';
import { ArchitectureSection } from './components/ArchitectureSection';
import { Footer } from './components/Footer';
import { ProcessingModal } from './components/ProcessingModal';
import { ActivityLogModal } from './components/ActivityLogModal';
import { SupabaseAuthModal } from './components/SupabaseAuthModal';
import { ComplianceModal } from './components/ComplianceModal';
import { AnalysesView } from './components/AnalysesView';
import { LibraryView } from './components/LibraryView';
import { DEFAULT_USER } from './lib/supabase';
import { EvidenceFile, SupabaseUser } from './types';

export default function App() {
  const [currentUser, setCurrentUser] = useState<SupabaseUser>(DEFAULT_USER);
  const [activeNav, setActiveNav] = useState<'Pipelines' | 'Analyses' | 'Library'>('Pipelines');
  const [currentStepId, setCurrentStepId] = useState<number>(3); // Step 3: Upload Evidence is active
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  
  // Modals state
  const [isProcessingOpen, setIsProcessingOpen] = useState(false);
  const [isActivityLogOpen, setIsActivityLogOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [complianceModalTab, setComplianceModalTab] = useState<'security' | 'compliance' | 'api' | null>(null);

  // Active file & case state
  const [activeCaseName, setActiveCaseName] = useState('V-2024-081A');
  const [activeEvidenceId, setActiveEvidenceId] = useState('');
  const [uploadedFile, setUploadedFile] = useState<EvidenceFile | null>(null);
  const [isArchitectureHighlighted, setIsArchitectureHighlighted] = useState(false);

  const handleNavigateToArchitecture = () => {
    setActiveNav('Pipelines');
    setTimeout(() => {
      const el = document.getElementById('architecture-overview');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setIsArchitectureHighlighted(true);
        setTimeout(() => {
          setIsArchitectureHighlighted(false);
        }, 3500);
      }
    }, 100);
  };

  // Handle responsive sidebar initial state
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Recent files list matching forensic pipeline
  const [recentFiles, setRecentFiles] = useState<EvidenceFile[]>([
    {
      id: 'evd-1',
      name: 'Interrogation_RM3_A.mp4',
      caseId: 'V-050',
      size: '5.2 GB',
      uploadedAt: '2024-10-24T14:22:18Z',
      hash: 'e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934ca495991b7852b855',
      status: 'verified',
    },
    {
      id: 'evd-2',
      name: 'Dashcam_Unit42.mov',
      caseId: 'V-079',
      size: '1.1 GB',
      uploadedAt: '2024-10-24T11:05:42Z',
      hash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
      status: 'verified',
    },
  ]);

  const handleFileUploaded = (file: EvidenceFile) => {
    setUploadedFile(file);
    setRecentFiles((prev) => [file, ...prev]);
  };

  const handleBeginProcessing = (data: { caseName: string; evidenceId: string; file: EvidenceFile | null }) => {
    setActiveCaseName(data.caseName);
    setActiveEvidenceId(data.evidenceId);
    if (data.file) {
      setUploadedFile(data.file);
    }
    setIsProcessingOpen(true);
  };

  const handleLogout = () => {
    setIsAuthModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#faf8f5] text-[#142e2e] flex flex-row font-['Manrope',sans-serif]">
      {/* Dynamic Collapsible Sidebar with Analyses, Library, Profile & Logout */}
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

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 transition-all">
        {/* Header Bar */}
        <Header
          user={currentUser}
          activeNav={activeNav}
          onNavChange={(nav) => setActiveNav(nav as any)}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onOpenActivityLog={() => setIsActivityLogOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          sidebarOpen={isSidebarOpen}
          onNavigateToArchitecture={handleNavigateToArchitecture}
        />

        {/* Main Workspace Container */}
        <main className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 pt-7 pb-12 flex-1">
          {activeNav === 'Pipelines' && (
            <div className="space-y-6 sm:space-y-7">
              {/* Top Stepper Card */}
              <ProcessPipeline
                currentStepId={currentStepId}
                onSelectStep={(stepId) => setCurrentStepId(stepId)}
              />

              {/* Middle Section: 2 Columns */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-7 items-stretch">
                {/* Left Column: Upload Evidence */}
                <div className="lg:col-span-8 flex">
                  <UploadSection
                    onBeginProcessing={handleBeginProcessing}
                    onFileUploaded={handleFileUploaded}
                  />
                </div>

                {/* Right Column: Chain of Custody */}
                <div className="lg:col-span-4 flex">
                  <ChainOfCustody
                    recentFiles={recentFiles}
                    onOpenActivityLog={() => setIsActivityLogOpen(true)}
                    onSelectFile={(f) => setUploadedFile(f)}
                  />
                </div>
              </div>

              {/* Bottom Architecture Section */}
              <ArchitectureSection isHighlighted={isArchitectureHighlighted} />
            </div>
          )}

          {activeNav === 'Analyses' && <AnalysesView />}

          {activeNav === 'Library' && (
            <LibraryView
              files={recentFiles}
              onOpenActivityLog={() => setIsActivityLogOpen(true)}
            />
          )}
        </main>

        {/* Footer */}
        <Footer
          onOpenCompliance={(tab) => setComplianceModalTab(tab)}
        />
      </div>

      {/* Interactive Modals */}
      <ProcessingModal
        isOpen={isProcessingOpen}
        onClose={() => setIsProcessingOpen(false)}
        caseName={activeCaseName}
        evidenceId={activeEvidenceId || 'EVD-894102'}
        file={uploadedFile}
        onCompleteStep={(stepId) => {
          setCurrentStepId(stepId);
          setActiveNav('Analyses');
        }}
      />

      <ActivityLogModal
        isOpen={isActivityLogOpen}
        onClose={() => setIsActivityLogOpen(false)}
      />

      <SupabaseAuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        currentUser={currentUser}
        onUpdateUser={(u) => setCurrentUser(u)}
      />

      <ComplianceModal
        isOpen={complianceModalTab !== null}
        initialTab={complianceModalTab || 'security'}
        onClose={() => setComplianceModalTab(null)}
      />
    </div>
  );
}
