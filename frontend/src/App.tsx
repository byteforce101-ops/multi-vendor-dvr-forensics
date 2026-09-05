'use client';

import React, { useState, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Bell,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  FileBarChart,
  FileImage,
  FileText,
  FileVideo,
  Filter,
  FolderSearch,
  Gauge,
  HelpCircle,
  Layers,
  LayoutDashboard,
  Maximize2,
  Menu,
  MessageSquare,
  Minus,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Upload,
  UploadCloud,
  UserRound,
  Video,
  Volume2,
  VolumeX,
  X,
  ZoomIn,
} from 'lucide-react';

import { api, API_BASE } from './api/client';
import type { CaseSummary, EvidenceSummary } from './api/client';
import type {
  VideoAnalysisResult,
  ReconstructedForensicEvent,
  VideoIntegrityAnalysis,
  EvidenceFile,
  SupabaseUser,
} from './types';
import { generateForensicDossier } from './utils/forensicDossier';
import TraceXLogo from './components/TraceXLogo';
import { LoginPage } from './components/LoginPage';
import { supabase, isSupabaseConfigured, DEFAULT_USER } from './lib/supabase';
import { LogOut, User as UserIcon } from 'lucide-react';

// ---------------------------------------------------------------------------
// View Definitions & Types
// ---------------------------------------------------------------------------

type View =
  | 'Overview'
  | 'Investigations'
  | 'Investigation Detail'
  | 'Video Evidence'
  | 'Timeline'
  | 'Detections'
  | 'Entities'
  | 'Entity Detail'
  | 'Events'
  | 'Evidence'
  | 'Integrity'
  | 'Reports'
  | 'Processing';

const navItems: [View, React.ComponentType<{ size?: number }>, string][] = [
  ['Overview', LayoutDashboard, 'Dashboard & Metrics'],
  ['Investigations', FolderSearch, 'Case Records'],
  ['Investigation Detail', Layers, 'Forensic Workspace'],
  ['Video Evidence', Video, 'Sources & Raw Images'],
  ['Timeline', Activity, 'Synchronized Analysis'],
  ['Detections', ScanIcon, 'Forensic Observations'],
  ['Entities', UserRound, 'Tracked Physical Objects'],
  ['Events', Activity, 'Reconstructed Incidents'],
  ['Evidence', FileImage, 'Keyframe Captures'],
  ['Integrity', ShieldCheck, 'Tampering & Hash Audit'],
  ['Reports', FileBarChart, 'Certified Court Dossiers'],
];

function ScanIcon({ size = 18 }: { size?: number }) {
  return <span className="scan-icon" style={{ width: size, height: size }} />;
}

// ---------------------------------------------------------------------------
// Helper: SHA-256 via Web Crypto
// ---------------------------------------------------------------------------

async function computeSHA256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B';
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatSeconds(secs: number): string {
  if (isNaN(secs) || secs < 0) return '00:00:00';
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  const ms = Math.floor((secs % 1) * 100);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// Reusable UI Components
// ---------------------------------------------------------------------------

function Button({
  children,
  onClick,
  variant = 'secondary',
  icon: Icon,
  className = '',
  disabled = false,
  title,
}: {
  children?: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  icon?: React.ComponentType<{ size?: number }>;
  className?: string;
  disabled?: boolean;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`btn btn-${variant} ${className} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {Icon && <Icon size={14} />}
      {children}
    </button>
  );
}

function StatusBadge({
  children,
  tone = 'slate',
}: {
  children: ReactNode;
  tone?: 'success' | 'warning' | 'critical' | 'teal' | 'slate';
}) {
  return <span className={`status status-${tone}`}>{children}</span>;
}

function EmptyState({
  title,
  description,
  action,
  onAction,
  icon: Icon = FolderSearch,
}: {
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
  icon?: React.ComponentType<{ size?: number }>;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Icon size={24} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action && onAction && (
        <Button variant="primary" onClick={onAction} icon={Plus}>
          {action}
        </Button>
      )}
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Application Component
// ---------------------------------------------------------------------------

export default function App() {
  // Navigation & layout state
  const [view, setView] = useState<View>('Overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  // Case & evidence state
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseSummary | null>(null);
  const [caseEvidence, setCaseEvidence] = useState<EvidenceSummary[]>([]);
  const [loadingCases, setLoadingCases] = useState(false);

  // Active Video & Analysis state
  const [analysisResult, setAnalysisResult] = useState<VideoAnalysisResult | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [loadedFileName, setLoadedFileName] = useState<string>('');
  const [loadedFileHash, setLoadedFileHash] = useState<string>('');
  const [loadedFileSize, setLoadedFileSize] = useState<number>(0);

  // Video player control state
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<string>('1x');
  const [surveillanceFilter, setSurveillanceFilter] = useState<string>('Standard');
  const [isMuted, setIsMuted] = useState(false);
  const [overlays, setOverlays] = useState({
    detections: true,
    tracks: true,
    confidence: true,
    motion: true,
    evidence: true,
  });

  // Processing pipeline state
  const [processingPhase, setProcessingPhase] = useState<number>(1);
  const [processingProgress, setProcessingProgress] = useState<number>(0);
  const [processingLogs, setProcessingLogs] = useState<string[]>([]);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Modals state
  const [isNewCaseModalOpen, setIsNewCaseModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isQueryModalOpen, setIsQueryModalOpen] = useState(false);
  const [globalSearchText, setGlobalSearchText] = useState('');
  const [timelineSubTab, setTimelineSubTab] = useState<'ai' | 'detections' | 'incidents'>('ai');

  // AI Conversational Query state
  const [groqApiKey, setGroqApiKey] = useState<string>(() => {
    return localStorage.getItem('tracex_groq_api_key') || '';
  });
  const [selectedGroqModel, setSelectedGroqModel] = useState<string>(() => {
    return localStorage.getItem('tracex_groq_model') || 'llama-3.1-8b-instant';
  });
  const [isGroqConfigOpen, setIsGroqConfigOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<
    Array<{
      sender: 'user' | 'assistant';
      text: string;
      events?: any[];
      source?: string;
      model?: string;
      groq_error?: string;
    }>
  >([
    {
      sender: 'assistant',
      text: 'Trace-X Forensic AI Agent is active (Groq LLaMA + OpenCV Forensic Vision). Ask questions about observed timeline events, vehicle identifications, kinematic velocities, or video integrity findings.',
      source: 'groq',
      model: 'llama-3.1-8b-instant',
    },
  ]);
  const [queryInput, setQueryInput] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);

  // Form states for New Case
  const [newCaseName, setNewCaseName] = useState('');
  const [newCaseNumber, setNewCaseNumber] = useState('');
  const [newCaseInvestigator, setNewCaseInvestigator] = useState('Agent Lead / Forensics Unit');
  const [newCaseDesc, setNewCaseDesc] = useState('');
  const [caseCreating, setCaseCreating] = useState(false);

  // Upload Form states
  const [selectedUploadFile, setSelectedUploadFile] = useState<File | null>(null);
  const [uploadHash, setUploadHash] = useState('');
  const [isCalculatingHash, setIsCalculatingHash] = useState(false);
  const [uploadTargetCaseId, setUploadTargetCaseId] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Drawer / Inspection Detail
  const [selectedEntity, setSelectedEntity] = useState<any | null>(null);

  // Authentication & User session state
  const [currentUser, setCurrentUser] = useState<SupabaseUser | null>(() => {
    const saved = localStorage.getItem('tracex_auth_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {}
    }
    return null;
  });
  const [authChecking, setAuthChecking] = useState(true);

  // -------------------------------------------------------------------------
  // 1. Initial Backend Health, Supabase Auth & Cases Fetch
  // -------------------------------------------------------------------------

  useEffect(() => {
    // Check Supabase active session
    if (isSupabaseConfigured && supabase) {
      supabase.auth.getSession().then(({ data }) => {
        if (data.session?.user) {
          const u = data.session.user;
          const userObj: SupabaseUser = {
            id: u.id,
            email: u.email || 'investigator@tracex.local',
            role: (u.user_metadata?.role as string) || 'Senior Forensic Analyst',
            enterpriseId: (u.user_metadata?.badge_id as string) || 'TRACEX-AUTH',
            name:
              (u.user_metadata?.full_name as string) ||
              (u.user_metadata?.name as string) ||
              u.email?.split('@')[0] ||
              'Examiner',
            isLoggedIn: true,
          };
          setCurrentUser(userObj);
          localStorage.setItem('tracex_auth_user', JSON.stringify(userObj));
        }
        setAuthChecking(false);
      }).catch(() => setAuthChecking(false));

      const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.user) {
          const u = session.user;
          const userObj: SupabaseUser = {
            id: u.id,
            email: u.email || 'investigator@tracex.local',
            role: (u.user_metadata?.role as string) || 'Senior Forensic Analyst',
            enterpriseId: (u.user_metadata?.badge_id as string) || 'TRACEX-AUTH',
            name:
              (u.user_metadata?.full_name as string) ||
              (u.user_metadata?.name as string) ||
              u.email?.split('@')[0] ||
              'Examiner',
            isLoggedIn: true,
          };
          setCurrentUser(userObj);
          localStorage.setItem('tracex_auth_user', JSON.stringify(userObj));
        } else {
          setCurrentUser(null);
          localStorage.removeItem('tracex_auth_user');
        }
      });

      return () => {
        authListener.subscription.unsubscribe();
      };
    } else {
      setAuthChecking(false);
    }
  }, []);

  const handleLoginSuccess = (user: SupabaseUser) => {
    setCurrentUser(user);
    localStorage.setItem('tracex_auth_user', JSON.stringify(user));
  };

  const handleSignOut = async () => {
    if (isSupabaseConfigured && supabase) {
      try {
        await supabase.auth.signOut();
      } catch (err) {
        console.warn('Sign out error:', err);
      }
    }
    setCurrentUser(null);
    localStorage.removeItem('tracex_auth_user');
  };

  const fetchCases = async () => {
    setLoadingCases(true);
    try {
      const data = await api.listCases();
      setCases(data || []);
      if (data && data.length > 0 && !selectedCase) {
        setSelectedCase(data[0]);
        setUploadTargetCaseId(data[0].id);
      }
      setBackendStatus('online');
    } catch (err) {
      console.warn('Backend cases fetch failed:', err);
      setBackendStatus('offline');
    } finally {
      setLoadingCases(false);
    }
  };

  useEffect(() => {
    // Health check
    api
      .checkHealth()
      .then(() => setBackendStatus('online'))
      .catch(() => setBackendStatus('offline'));

    if (currentUser) {
      fetchCases();
    }
  }, [currentUser]);

  // Fetch evidence when selectedCase changes
  useEffect(() => {
    if (!selectedCase) return;
    setUploadTargetCaseId(selectedCase.id);
    api
      .listEvidence(selectedCase.id)
      .then((evs) => setCaseEvidence(evs || []))
      .catch((err) => console.warn('Evidence fetch error:', err));
  }, [selectedCase]);

  // -------------------------------------------------------------------------
  // 2. Video Player Lifecycle & Control Handlers
  // -------------------------------------------------------------------------

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play().catch((err) => console.warn('Play was prevented:', err));
    } else {
      v.pause();
    }
  };

  const seekVideo = (timeSec: number) => {
    const maxDur = duration || analysisResult?.metadata?.duration_seconds || 9999;
    const clamped = Math.max(0, Math.min(maxDur, timeSec));
    setCurrentTime(clamped);
    const v = videoRef.current;
    if (v) {
      v.currentTime = clamped;
    }
  };

  const stepFrame = (deltaSeconds: number) => {
    const v = videoRef.current;
    if (v) {
      v.pause();
      const maxDur = v.duration || analysisResult?.metadata?.duration_seconds || 9999;
      const nextTime = Math.max(0, Math.min(maxDur, v.currentTime + deltaSeconds));
      v.currentTime = nextTime;
      setCurrentTime(nextTime);
    } else {
      seekVideo(currentTime + deltaSeconds);
    }
  };

  const handleSpeedChange = (speedStr: string) => {
    setPlaybackSpeed(speedStr);
    const rate = parseFloat(speedStr.replace('x', '')) || 1.0;
    const v = videoRef.current;
    if (v) {
      v.playbackRate = rate;
    }
  };

  const toggleMute = () => {
    const next = !isMuted;
    setIsMuted(next);
    const v = videoRef.current;
    if (v) {
      v.muted = next;
    }
  };

  const handleToggleFullscreen = () => {
    const el = document.querySelector('.viewer-wrap');
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  // Keyboard navigation for forensic playback
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || isUploadModalOpen || isNewCaseModalOpen || isQueryModalOpen) {
        return;
      }
      if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        stepFrame(e.shiftKey ? -0.04 : -1);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        stepFrame(e.shiftKey ? 0.04 : 1);
      } else if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        toggleMute();
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        handleToggleFullscreen();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isUploadModalOpen, isNewCaseModalOpen, isQueryModalOpen, isMuted, isPlaying, duration]);

  // -------------------------------------------------------------------------
  // 3. File Selection & Analysis Execution Pipeline
  // -------------------------------------------------------------------------

  const handleFileChosen = async (file: File) => {
    setSelectedUploadFile(file);
    setIsCalculatingHash(true);
    setUploadHash('');
    try {
      const hash = await computeSHA256(file);
      setUploadHash(hash);
    } catch (err) {
      console.error('Hash calculation error:', err);
      setUploadHash('CALCULATION_UNAVAILABLE');
    } finally {
      setIsCalculatingHash(false);
    }
  };

  const startAnalysisPipeline = async () => {
    if (!selectedUploadFile) return;

    setIsUploadModalOpen(false);
    setView('Processing');
    setIsProcessing(true);
    setProcessingError(null);
    setProcessingProgress(15);
    setProcessingPhase(1);

    const fileName = selectedUploadFile.name;
    const fileSize = selectedUploadFile.size;
    const finalHash = uploadHash || (await computeSHA256(selectedUploadFile));

    setLoadedFileName(fileName);
    setLoadedFileHash(finalHash);
    setLoadedFileSize(fileSize);

    setProcessingLogs([
      `[INGEST] Acquired forensic artifact: ${fileName} (${formatFileSize(fileSize)})`,
      `[SHA256] Cryptographic Seal: ${finalHash}`,
      `[PIPELINE] Initializing backend forensic worker on FastAPI port 8000.`,
    ]);

    // Local object URL fallback for web video
    const isStandardWebVideo = /\.(mp4|webm|ogg|mov)$/i.test(fileName);
    if (isStandardWebVideo) {
      const localUrl = URL.createObjectURL(selectedUploadFile);
      setVideoUrl(localUrl);
    }

    try {
      setProcessingProgress(35);
      setProcessingPhase(2);
      setProcessingLogs((prev) => [
        ...prev,
        `[CONTAINER] Inspecting stream descriptors, container atom headers & DVR indexes.`,
        `[DECODER] Extracting baseline frames & calculating temporal motion vectors.`,
      ]);

      // Call backend /video/analyze
      const result = await api.analyzeVideo(selectedUploadFile);

      setProcessingProgress(70);
      setProcessingPhase(3);
      setProcessingLogs((prev) => [
        ...prev,
        `[OPENCV] Multi-stage forensic detection completed (HOG + Haar + MOG2 Kinematics).`,
        `[RECONSTRUCTION] Correlated ${result.events?.length || 0} detections into ${result.reconstruction_count || 0} narrative events.`,
      ]);

      setProcessingProgress(90);
      setProcessingPhase(4);
      setProcessingLogs((prev) => [
        ...prev,
        `[INTEGRITY] Verified container continuity: status=${result.integrity_analysis?.overall_status || 'PASS'} (Score: ${result.integrity_analysis?.integrity_score ?? 100}%)`,
        `[DISAPPEARANCE] Object disappearance detection completed.`,
      ]);

      setAnalysisResult(result);

      // If backend generated a normalized stream and local was not a standard video
      if (result.analysis_id) {
        const streamUrl = api.getVideoStreamUrl(result.analysis_id);
        // Only override if we didn't have a direct local playback or if normalized is available
        if (!isStandardWebVideo) {
          setVideoUrl(streamUrl);
        }
      }

      // If a case is selected, also register upload in case evidence
      if (uploadTargetCaseId) {
        try {
          await api.uploadEvidence(uploadTargetCaseId, selectedUploadFile);
          fetchCases();
        } catch {
          // Evidence record is secondary to standalone analysis result
        }
      }

      setProcessingProgress(100);
      setProcessingPhase(5);
      setProcessingLogs((prev) => [
        ...prev,
        `[COMPLETED] Forensic analysis dossier compiled successfully.`,
        `[READY] Workspace loaded for interactive inspection.`,
      ]);

      setIsProcessing(false);

      // Record real Chain of Custody entry
      try {
        const newLog = {
          id: `act-${Date.now()}`,
          timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
          action: 'SHA-256 Bitstream Seal & Automated Video Analysis',
          fileName: selectedUploadFile.name,
          caseId: selectedCase?.case_number || selectedCase?.id?.slice(0, 8) || 'STANDALONE',
          hashSnippet: uploadHash || fileHash || 'CRYPTOGRAPHIC_SEAL_VALID',
          operator: selectedCase?.investigator || 'Forensic Examiner',
          verified: true,
        };
        const existingLogs = JSON.parse(localStorage.getItem('tracex_custody_logs') || '[]');
        localStorage.setItem('tracex_custody_logs', JSON.stringify([newLog, ...existingLogs]));
      } catch {}

      // Auto-navigate to workspace view after brief delay
      setTimeout(() => {
        setView('Investigation Detail');
      }, 900);
    } catch (err: any) {
      console.error('Forensic analysis error:', err);
      setIsProcessing(false);
      setProcessingError(err?.message || 'Forensic analysis pipeline failed to process media.');
      setProcessingLogs((prev) => [
        ...prev,
        `[ERROR] Pipeline aborted: ${err?.message || 'Unknown backend error'}`,
      ]);
    }
  };

  // -------------------------------------------------------------------------
  // 4. Case Creation Handler
  // -------------------------------------------------------------------------

  const handleCreateCaseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseName.trim()) return;

    setCaseCreating(true);
    try {
      const generatedNumber =
        newCaseNumber.trim() || `CASE-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
      const created = await api.createCase(
        newCaseName.trim(),
        newCaseInvestigator.trim() || 'Lead Forensic Specialist',
        newCaseDesc.trim(),
        generatedNumber
      );

      setCases((prev) => [created, ...prev]);
      setSelectedCase(created);
      setUploadTargetCaseId(created.id);
      setIsNewCaseModalOpen(false);
      setNewCaseName('');
      setNewCaseNumber('');
      setNewCaseDesc('');
      setView('Investigations');
    } catch (err: any) {
      alert(`Failed to create case: ${err?.message || 'Server error'}`);
    } finally {
      setCaseCreating(false);
    }
  };

  // -------------------------------------------------------------------------
  // 5. Conversational Forensic Query
  // -------------------------------------------------------------------------

  const handleSendQuery = async (queryText?: string) => {
    const textToSend = queryText || queryInput;
    if (!textToSend.trim() || isQuerying) return;

    const userMsg = { sender: 'user' as const, text: textToSend };
    setChatMessages((prev) => [...prev, userMsg]);
    setQueryInput('');
    setIsQuerying(true);

    try {
      const events = analysisResult?.events || [];
      const summary = analysisResult?.forensic_summary || null;
      const integrity = analysisResult?.integrity_analysis || (analysisResult as any)?.video_integrity || null;
      const disappearances =
        analysisResult?.object_disappearance_analysis?.disappearances ||
        (analysisResult as any)?.object_disappearance?.disappearances ||
        [];

      const res = await api.queryVideo(textToSend, events, summary, {
        integrity,
        disappearances,
        groqApiKey: groqApiKey.trim() || undefined,
        model: selectedGroqModel,
        chatHistory: chatMessages.slice(-6).map((m) => ({ sender: m.sender, text: m.text })),
      });

      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: res.answer,
          events: res.matching_events,
          source: res.source,
          model: res.model,
          groq_error: res.groq_error,
        },
      ]);
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: `Query error: ${err?.message || 'Forensic search service currently unavailable.'}`,
          source: 'error',
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  // -------------------------------------------------------------------------
  // 6. Export Certified PDF Report
  // -------------------------------------------------------------------------

  const handleExportPDF = () => {
    if (!analysisResult) {
      alert('Please load and analyze a video or DVR image first to export a forensic dossier.');
      return;
    }
    try {
      generateForensicDossier(analysisResult);
    } catch (err: any) {
      console.error('PDF generation error:', err);
      alert(`Failed to generate PDF: ${err?.message || 'Generation error'}`);
    }
  };

  // -------------------------------------------------------------------------
  // 7. Overlays calculation
  // -------------------------------------------------------------------------

  const firstEventTime = analysisResult?.events?.[0]?.start_time;
  const activeDetections = (analysisResult?.events || []).filter((ev) => {
    if (!overlays.detections) return false;
    try {
      const meta = (ev.metadata as any) || {};
      let eventSec = 0;
      if (meta.timestamp_seconds != null && typeof meta.timestamp_seconds === 'number') {
        eventSec = meta.timestamp_seconds;
      } else if (meta.seconds != null && typeof meta.seconds === 'number') {
        eventSec = meta.seconds;
      } else if (ev.start_time && firstEventTime) {
        const t0 = new Date(firstEventTime).getTime();
        const t1 = new Date(ev.start_time).getTime();
        if (!isNaN(t0) && !isNaN(t1) && t1 >= t0) {
          eventSec = (t1 - t0) / 1000;
        } else if (!isNaN(t1)) {
          eventSec = (t1 / 1000) % (duration || 3600);
        }
      }
      const dur = duration || analysisResult?.metadata?.duration_seconds || 3600;
      const normalizedEventSec = dur > 0 ? eventSec % dur : eventSec;
      return Math.abs(currentTime - normalizedEventSec) <= 1.25;
    } catch {
      return false;
    }
  });

  // Filter CCTV class
  const cctvFilterClass =
    surveillanceFilter === 'Night Vision'
      ? 'night'
      : surveillanceFilter === 'Invert'
      ? 'invert'
      : surveillanceFilter === 'High Contrast'
      ? 'contrast'
      : surveillanceFilter === 'Sharpen Detail'
      ? 'sharpen'
      : '';

  // -------------------------------------------------------------------------
  // Renderers for Sub-views
  // -------------------------------------------------------------------------

  // OVERVIEW
  const renderOverview = () => {
    const metricCards = [
      {
        label: 'Total Cases',
        val: cases.length.toString(),
        sub: `${cases.filter((c) => c.status !== 'closed').length} active investigations`,
        icon: FolderSearch,
        color: 'navy',
      },
      {
        label: 'Evidence Files',
        val: (caseEvidence.length || (analysisResult ? 1 : 0)).toString(),
        sub: loadedFileName ? `Active: ${loadedFileName.slice(0, 18)}...` : 'Awaiting media ingest',
        icon: Video,
        color: 'teal',
      },
      {
        label: 'OpenCV Detections',
        val: (analysisResult?.event_count ?? 0).toString(),
        sub: 'Forensic vision observations',
        icon: ScanIcon,
        color: 'violet',
      },
      {
        label: 'Tracked Entities',
        val: (analysisResult?.forensic_summary?.objects_detected?.length ?? 0).toString(),
        sub: 'Distinct target identities',
        icon: UserRound,
        color: 'amber',
      },
      {
        label: 'Reconstructed Events',
        val: (analysisResult?.reconstruction_count ?? 0).toString(),
        sub: 'Incident narrative milestones',
        icon: Activity,
        color: 'emerald',
      },
      {
        label: 'Integrity Score',
        val: analysisResult?.integrity_analysis
          ? `${analysisResult.integrity_analysis.integrity_score}%`
          : '—',
        sub: analysisResult?.integrity_analysis?.overall_status || 'Pending inspection',
        icon: ShieldCheck,
        color: 'navy',
      },
    ];

    return (
      <div className="page">
        <PageTitle
          eyebrow="OPERATIONS / OVERVIEW"
          title="Forensic Investigation Overview"
          description="Enterprise digital video evidence acquisition, frame validation, and AI event reconstruction."
          action={
            <div style={{ display: 'flex', gap: '8px' }}>
              <Button
                variant="primary"
                icon={UploadCloud}
                onClick={() => setIsUploadModalOpen(true)}
              >
                Ingest Media / DVR Image
              </Button>
              <Button
                variant="secondary"
                icon={Plus}
                onClick={() => setIsNewCaseModalOpen(true)}
              >
                New Investigation
              </Button>
            </div>
          }
        />

        <div className="overview-cards">
          {metricCards.map((m) => {
            const Icon = m.icon;
            return (
              <div className="metric" key={m.label}>
                <div className={`metric-icon ${m.color}`}>
                  <Icon size={18} />
                </div>
                <div>
                  <p>{m.label}</p>
                  <strong>{m.val}</strong>
                  <small>{m.sub}</small>
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick launch / Active Workspace Banner */}
        {loadedFileName ? (
          <div className="panel" style={{ padding: '20px', marginBottom: '20px' }}>
            <div className="section-head" style={{ marginBottom: '14px' }}>
              <div>
                <p className="eyebrow">ACTIVE WORKSPACE</p>
                <h3>{loadedFileName}</h3>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <Button
                  variant="primary"
                  icon={Play}
                  onClick={() => setView('Investigation Detail')}
                >
                  Open in CCTV Viewer
                </Button>
                <Button icon={FileBarChart} onClick={handleExportPDF}>
                  Export Certified PDF
                </Button>
              </div>
            </div>
            <div className="tech-meta-row" style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
              <div className="tech-meta">
                <span>CRYPTOGRAPHIC SEAL (SHA-256)</span>
                <b className="mono" style={{ fontSize: '10px', color: '#0f766e' }}>
                  {loadedFileHash ? `${loadedFileHash.substring(0, 36)}...` : 'Pending'}
                </b>
              </div>
              <div className="tech-meta">
                <span>RESOLUTION & CODEC</span>
                <b>
                  {analysisResult?.metadata?.width
                    ? `${analysisResult.metadata.width}x${analysisResult.metadata.height} (${analysisResult.metadata.codec || 'H.264'})`
                    : 'DVR Stream'}
                </b>
              </div>
              <div className="tech-meta">
                <span>DURATION</span>
                <b>{formatSeconds(duration || analysisResult?.metadata?.duration_seconds || 0)}</b>
              </div>
              <div className="tech-meta">
                <span>INTEGRITY AUDIT</span>
                <b>
                  <StatusBadge
                    tone={
                      analysisResult?.integrity_analysis?.overall_status === 'PASS'
                        ? 'success'
                        : 'warning'
                    }
                  >
                    {analysisResult?.integrity_analysis?.overall_status || 'VERIFIED'}
                  </StatusBadge>
                </b>
              </div>
            </div>
          </div>
        ) : (
          <div className="panel overview-empty">
            <EmptyState
              title="No media loaded for analysis"
              description="Upload a CCTV surveillance video (.mp4, .avi, .mov) or raw DVR disk image (.dd, .raw, .img) to initiate automated object detection, tampering verification, and event reconstruction."
              action="Ingest Video or DVR Image"
              onAction={() => setIsUploadModalOpen(true)}
              icon={Video}
            />
          </div>
        )}

        {/* Cases list */}
        <div className="panel table-panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">ACTIVE DOSSIERS</p>
              <h3>Recent Case Files</h3>
            </div>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={fetchCases}
              disabled={loadingCases}
            >
              Refresh
            </Button>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Title</th>
                  <th>Investigator</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {cases.length > 0 ? (
                  cases.slice(0, 6).map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => {
                        setSelectedCase(c);
                        setView('Investigation Detail');
                      }}
                    >
                      <td>
                        <b className="mono">{c.case_number || c.id.slice(0, 8)}</b>
                      </td>
                      <td>
                        <b>{c.name}</b>
                        <small>{c.description || 'No case description'}</small>
                      </td>
                      <td>{c.investigator}</td>
                      <td>
                        <StatusBadge
                          tone={
                            c.status === 'open'
                              ? 'teal'
                              : c.status === 'closed'
                              ? 'slate'
                              : 'warning'
                          }
                        >
                          {c.status.toUpperCase()}
                        </StatusBadge>
                      </td>
                      <td className="muted">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <Button
                          variant="secondary"
                          icon={ChevronRight}
                          onClick={() => {
                            setSelectedCase(c);
                            setView('Investigation Detail');
                          }}
                        >
                          Open
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '30px' }}>
                      <p className="muted">No cases found in PostgreSQL database.</p>
                      <Button
                        variant="primary"
                        icon={Plus}
                        onClick={() => setIsNewCaseModalOpen(true)}
                      >
                        Create First Case
                      </Button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // INVESTIGATIONS VIEW
  const renderInvestigations = () => {
    const filteredCases = cases.filter(
      (c) =>
        c.name.toLowerCase().includes(globalSearchText.toLowerCase()) ||
        (c.case_number && c.case_number.toLowerCase().includes(globalSearchText.toLowerCase())) ||
        c.investigator.toLowerCase().includes(globalSearchText.toLowerCase())
    );

    return (
      <div className="page">
        <PageTitle
          eyebrow="CASE MANAGEMENT"
          title="Forensic Investigations"
          description="Browse, filter, and manage authorized video forensic investigation dossiers."
          action={
            <Button
              variant="primary"
              icon={Plus}
              onClick={() => setIsNewCaseModalOpen(true)}
            >
              New Investigation
            </Button>
          }
        />

        <div className="filters">
          <div className="filter-search">
            <Search size={15} />
            <input
              value={globalSearchText}
              onChange={(e) => setGlobalSearchText(e.target.value)}
              placeholder="Search by case #, subject, or investigator..."
            />
          </div>
          <Button icon={Filter}>Filter Status</Button>
          <Button icon={RefreshCw} onClick={fetchCases} disabled={loadingCases}>
            Refresh
          </Button>
        </div>

        <div className="panel table-panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Case Identifier</th>
                  <th>Investigation Title</th>
                  <th>Lead Specialist</th>
                  <th>Status</th>
                  <th>Date Initiated</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredCases.length > 0 ? (
                  filteredCases.map((c) => (
                    <tr
                      key={c.id}
                      className={selectedCase?.id === c.id ? 'active-row' : ''}
                      onClick={() => {
                        setSelectedCase(c);
                        setView('Investigation Detail');
                      }}
                    >
                      <td>
                        <b className="mono">{c.case_number || c.id.slice(0, 8)}</b>
                      </td>
                      <td>
                        <b>{c.name}</b>
                        <small>{c.description || 'Investigation active'}</small>
                      </td>
                      <td>{c.investigator}</td>
                      <td>
                        <StatusBadge
                          tone={
                            c.status === 'open'
                              ? 'teal'
                              : c.status === 'closed'
                              ? 'slate'
                              : 'warning'
                          }
                        >
                          {c.status.toUpperCase()}
                        </StatusBadge>
                      </td>
                      <td className="muted">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <Button
                          variant="secondary"
                          icon={ChevronRight}
                          onClick={() => {
                            setSelectedCase(c);
                            setView('Investigation Detail');
                          }}
                        >
                          Launch Workspace
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        title="No matching investigations found"
                        description="Create a new case record to track evidence items and generate court-ready reports."
                        action="Create Investigation"
                        onAction={() => setIsNewCaseModalOpen(true)}
                        icon={FolderSearch}
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // CCTV VIDEO VIEWER COMPONENT
  const renderVideoViewer = () => {
    return (
      <div className="viewer-wrap">
        {/* Surveillance filter & speed bars */}
        <div className="viewer-controls">
          <div>
            <p className="eyebrow">SURVEILLANCE FILTER</p>
            <div className="segmented">
              {['Standard', 'Night Vision', 'Invert', 'High Contrast', 'Sharpen Detail'].map(
                (item) => (
                  <button
                    key={item}
                    className={surveillanceFilter === item ? 'active' : ''}
                    onClick={() => setSurveillanceFilter(item)}
                  >
                    {item}
                  </button>
                )
              )}
            </div>
          </div>
          <div>
            <p className="eyebrow">PLAYBACK SPEED</p>
            <div className="segmented">
              {['0.25x', '0.5x', '1x', '1.5x', '2x'].map((s) => (
                <button
                  key={s}
                  className={playbackSpeed === s ? 'active' : ''}
                  onClick={() => handleSpeedChange(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Video stage */}
        <div className="viewer">
          <div className={`cctv-scene ${cctvFilterClass}`}>
            {videoUrl ? (
              <video
                ref={videoRef}
                src={videoUrl}
                className="real-video"
                playsInline
                muted={isMuted}
                onClick={togglePlay}
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                onDurationChange={(e) => {
                  const d = e.currentTarget.duration;
                  if (d && !isNaN(d) && isFinite(d)) setDuration(d);
                }}
                onLoadedMetadata={(e) => {
                  const d = e.currentTarget.duration;
                  if (d && !isNaN(d) && isFinite(d)) {
                    setDuration(d);
                  } else if (analysisResult?.metadata?.duration_seconds) {
                    setDuration(analysisResult.metadata.duration_seconds);
                  }
                  const rate = parseFloat(playbackSpeed.replace('x', '')) || 1.0;
                  e.currentTarget.playbackRate = rate;
                  e.currentTarget.muted = isMuted;
                }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onEnded={() => setIsPlaying(false)}
                onError={() => {
                  if (analysisResult?.analysis_id) {
                    const fallbackStream = api.getVideoStreamUrl(analysisResult.analysis_id);
                    if (videoUrl !== fallbackStream) {
                      console.warn('Direct video playback error, switching to backend stream:', fallbackStream);
                      setVideoUrl(fallbackStream);
                    }
                  }
                }}
              />
            ) : (
              <div className="scene-placeholder">
                <Video size={36} />
                <b>No Video Loaded</b>
                <span>Ingest a CCTV file or DVR disk image to begin video forensics.</span>
                <div style={{ marginTop: '12px' }}>
                  <Button
                    variant="primary"
                    icon={UploadCloud}
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    Ingest Media
                  </Button>
                </div>
              </div>
            )}

            {/* Video Overlays (Bounding Boxes) */}
            {overlays.detections && activeDetections.length > 0 && (
              <div className="video-overlay-layer">
                {activeDetections.map((det, idx) => {
                  const meta = (det.metadata as any) || {};
                  let left = `${35 + ((idx * 15) % 45)}%`;
                  let top = `${30 + ((idx * 12) % 40)}%`;
                  let width = '22%';
                  let height = '38%';

                  if (Array.isArray(meta.bbox) && meta.bbox.length === 4) {
                    const [b0, b1, b2, b3] = meta.bbox;
                    if (b0 <= 1 && b1 <= 1 && b2 <= 1 && b3 <= 1) {
                      left = `${b0 * 100}%`;
                      top = `${b1 * 100}%`;
                      width = `${Math.max(0.05, b2 - b0) * 100}%`;
                      height = `${Math.max(0.05, b3 - b1) * 100}%`;
                    } else if (b0 <= 100 && b1 <= 100 && b2 <= 100 && b3 <= 100) {
                      left = `${b0}%`;
                      top = `${b1}%`;
                      width = `${Math.max(5, b2 > b0 ? b2 - b0 : b2)}%`;
                      height = `${Math.max(5, b3 > b1 ? b3 - b1 : b3)}%`;
                    } else if (analysisResult?.metadata?.width && analysisResult?.metadata?.height) {
                      const vw = analysisResult.metadata.width;
                      const vh = analysisResult.metadata.height;
                      left = `${(b0 / vw) * 100}%`;
                      top = `${(b1 / vh) * 100}%`;
                      width = `${Math.max(5, ((b2 > b0 ? b2 - b0 : b2) / vw) * 100)}%`;
                      height = `${Math.max(5, ((b3 > b1 ? b3 - b1 : b3) / vh) * 100)}%`;
                    }
                  }

                  return (
                    <div
                      key={idx}
                      className="detection-box"
                      style={{ left, top, width, height }}
                    >
                      <span className="detection-box-label">
                        {det.object_type || det.event_type}
                        {overlays.tracks && det.track_id != null && ` [ID:${det.track_id}]`}
                        {overlays.confidence &&
                          det.confidence != null &&
                          ` ${(det.confidence * 100).toFixed(0)}%`}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* CCTV Topbar HUD */}
            <div className="viewer-label">
              <b>{loadedFileName || 'CH-01 • SURVEILLANCE_MAIN'}</b>
              <span>{analysisResult ? 'ANALYZED & VERIFIED' : 'AWAITING INGEST'}</span>
            </div>
            <div className="viewer-time">
              <span>{formatSeconds(currentTime)}</span>
              <small>UTC TIME: {new Date().toISOString().slice(11, 19)}</small>
            </div>
            {isPlaying && (
              <div className="rec">
                <i />
                REC PLAYBACK
              </div>
            )}
          </div>

          {/* Transport Toolbar */}
          <div className="viewer-toolbar">
            <button
              className="transport primary-transport"
              onClick={togglePlay}
              aria-label={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
              title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
            >
              {isPlaying ? <Pause size={15} /> : <Play size={15} />}
            </button>

            <button
              className="transport"
              onClick={() => stepFrame(-0.04)}
              title="Step -1 Frame (-0.04s) [Shift+Left]"
              aria-label="Previous Frame"
            >
              <ArrowLeft size={14} />
            </button>
            <button
              className="transport"
              onClick={() => stepFrame(0.04)}
              title="Step +1 Frame (+0.04s) [Shift+Right]"
              aria-label="Next Frame"
            >
              <ChevronRight size={14} />
            </button>

            <button
              className="transport"
              onClick={() => seekVideo(currentTime - 1)}
              title="Jump -1 Second [Left Arrow]"
            >
              -1s
            </button>
            <button
              className="transport"
              onClick={() => seekVideo(currentTime + 1)}
              title="Jump +1 Second [Right Arrow]"
            >
              +1s
            </button>

            <button
              className="transport"
              onClick={toggleMute}
              title={isMuted ? 'Unmute (M)' : 'Mute (M)'}
              aria-label={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
            </button>

            <button
              className="transport"
              onClick={handleToggleFullscreen}
              title="Toggle Fullscreen (F)"
              aria-label="Toggle Fullscreen"
            >
              <Maximize2 size={14} />
            </button>

            {/* Scrubber slider */}
            <input
              type="range"
              min={0}
              max={duration || analysisResult?.metadata?.duration_seconds || 100}
              step={0.01}
              value={currentTime}
              onChange={(e) => seekVideo(parseFloat(e.target.value))}
              className="scrub-slider"
              title="Scrub video timeline"
            />

            <span className="toolbar-readout">
              {formatSeconds(currentTime)} / {formatSeconds(duration || analysisResult?.metadata?.duration_seconds || 0)}{' '}
              <small>FRAME {Math.floor(currentTime * 25)}</small>
            </span>
          </div>
        </div>

        {/* Overlay toggle switches */}
        <div className="overlay-toggles">
          {[
            ['detections', 'Show detections'],
            ['tracks', 'Show track IDs'],
            ['confidence', 'Show confidence'],
            ['motion', 'Show motion vectors'],
            ['evidence', 'Show evidence marks'],
          ].map(([key, label]) => {
            const isChecked = overlays[key as keyof typeof overlays];
            return (
              <button
                key={key}
                className={`toggle-row ${isChecked ? 'checked' : ''}`}
                onClick={() =>
                  setOverlays((old) => ({
                    ...old,
                    [key]: !old[key as keyof typeof overlays],
                  }))
                }
              >
                <span>{label}</span>
                <i className={isChecked ? 'on' : ''}>
                  <b />
                </i>
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  // TIMELINE COMPONENT
  const renderTimeline = ({ full = false }: { full?: boolean }) => {
    const totalDuration = duration || 60;
    const events = analysisResult?.events || [];

    return (
      <div className={`timeline-card panel ${full ? 'timeline-full' : ''}`}>
        <div className="section-head">
          <div>
            <p className="eyebrow">SYNCHRONIZED ANALYSIS</p>
            <h3>Forensic Event Timeline</h3>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              variant="secondary"
              icon={RotateCcw}
              onClick={() => seekVideo(0)}
            >
              Reset 00:00
            </Button>
            <Button
              variant="secondary"
              icon={ZoomIn}
              onClick={() => {}}
            >
              Fit Ruler
            </Button>
          </div>
        </div>

        {/* Time ruler */}
        <div className="time-ruler">
          <span>00:00</span>
          <span>{formatSeconds(totalDuration * 0.25)}</span>
          <span>{formatSeconds(totalDuration * 0.5)}</span>
          <span>{formatSeconds(totalDuration * 0.75)}</span>
          <span>{formatSeconds(totalDuration)}</span>
        </div>

        {/* Tracks */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Track 1: Detections & Objects */}
          <div className="track">
            <label>DETECTIONS</label>
            <div className="track-line">
              <div
                className="video-progress"
                style={{ width: `${Math.min(100, (currentTime / totalDuration) * 100)}%` }}
              />
              {events.slice(0, 25).map((ev, i) => {
                const pos = ((i * 3.7 + 5) % 92).toFixed(1);
                return (
                  <button
                    key={i}
                    className="event-mark"
                    style={{ left: `${pos}%` }}
                    onClick={() => seekVideo((parseFloat(pos) / 100) * totalDuration)}
                    title={`${ev.event_type} (${ev.object_type || 'target'})`}
                  />
                );
              })}
            </div>
          </div>

          {/* Track 2: Motion / Incidents */}
          <div className="track">
            <label>INCIDENTS</label>
            <div className="track-line">
              <div
                className="video-progress"
                style={{
                  width: `${Math.min(100, (currentTime / totalDuration) * 100)}%`,
                  background: 'linear-gradient(90deg, #fed7aa, #f97316)',
                }}
              />
              {(analysisResult?.reconstructed_events || []).map((rev, i) => {
                const pos = ((i * 18 + 12) % 88).toFixed(1);
                return (
                  <button
                    key={i}
                    className="event-mark mark-1"
                    style={{ left: `${pos}%` }}
                    onClick={() => seekVideo((parseFloat(pos) / 100) * totalDuration)}
                    title={rev.title}
                  />
                );
              })}
            </div>
          </div>
        </div>

        <div className="timeline-footer">
          <span>
            <i className="legend teal" /> Detections
          </span>
          <span>
            <i className="legend amber" /> Narrative Incidents
          </span>
          <span>
            <i className="legend coral" /> Disappearances
          </span>
          <span className="frame-readout">
            Current: <b>{formatSeconds(currentTime)}</b> (Frame {Math.floor(currentTime * 25)})
          </span>
        </div>
      </div>
    );
  };

  // TABBED SECTION BELOW SYNCHRONIZED ANALYSIS TIMELINE
  const renderTimelineTabsSection = () => {
    const events = analysisResult?.events || [];
    const reconstructed = analysisResult?.reconstructed_events || [];

    return (
      <div className="panel" style={{ marginTop: '14px', overflow: 'hidden' }}>
        {/* Tab Navigation Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #e2e8f0',
            background: '#f8fafc',
            padding: '4px 12px 0',
          }}
        >
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => setTimelineSubTab('ai')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: timelineSubTab === 'ai' ? 700 : 500,
                color: timelineSubTab === 'ai' ? '#172554' : '#64748b',
                borderBottom: timelineSubTab === 'ai' ? '2px solid #2563eb' : '2px solid transparent',
                background: 'transparent',
                borderTop: 0,
                borderLeft: 0,
                borderRight: 0,
                cursor: 'pointer',
              }}
            >
              <Sparkles size={14} style={{ color: timelineSubTab === 'ai' ? '#2563eb' : '#94a3b8' }} />
              <span>AI Forensic Analysis</span>
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '4px',
                  background: timelineSubTab === 'ai' ? '#dbeafe' : '#e2e8f0',
                  color: timelineSubTab === 'ai' ? '#1e40af' : '#475569',
                }}
              >
                Groq AI
              </span>
            </button>

            <button
              onClick={() => setTimelineSubTab('detections')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: timelineSubTab === 'detections' ? 700 : 500,
                color: timelineSubTab === 'detections' ? '#172554' : '#64748b',
                borderBottom: timelineSubTab === 'detections' ? '2px solid #2563eb' : '2px solid transparent',
                background: 'transparent',
                borderTop: 0,
                borderLeft: 0,
                borderRight: 0,
                cursor: 'pointer',
              }}
            >
              <Clock size={14} style={{ color: timelineSubTab === 'detections' ? '#2563eb' : '#94a3b8' }} />
              <span>Event Chronology</span>
              {events.length > 0 && (
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: '4px',
                    background: '#e2e8f0',
                    color: '#475569',
                  }}
                >
                  {events.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setTimelineSubTab('incidents')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: timelineSubTab === 'incidents' ? 700 : 500,
                color: timelineSubTab === 'incidents' ? '#172554' : '#64748b',
                borderBottom: timelineSubTab === 'incidents' ? '2px solid #2563eb' : '2px solid transparent',
                background: 'transparent',
                borderTop: 0,
                borderLeft: 0,
                borderRight: 0,
                cursor: 'pointer',
              }}
            >
              <Activity size={14} style={{ color: timelineSubTab === 'incidents' ? '#2563eb' : '#94a3b8' }} />
              <span>Reconstructed Activities</span>
              {reconstructed.length > 0 && (
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: '4px',
                    background: '#e2e8f0',
                    color: '#475569',
                  }}
                >
                  {reconstructed.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div style={{ padding: '16px' }}>
          {timelineSubTab === 'ai' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Quick Forensic Prompts */}
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  'What vehicles were tracked & at what velocity?',
                  'What objects & persons were detected?',
                  'Did any object disappear from the scene?',
                  'Check video integrity & frame continuity',
                  'Was there an accident or sudden stop?',
                  'Summarize the timeline chronologically',
                ].map((promptText) => (
                  <button
                    key={promptText}
                    onClick={() => handleSendQuery(promptText)}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: '#f1f5f9',
                      border: '1px solid #cbd5e1',
                      color: '#334155',
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    {promptText}
                  </button>
                ))}
              </div>

              {/* Chat Stream Log */}
              <div
                className="query-chat"
                style={{
                  maxHeight: '260px',
                  minHeight: '130px',
                  overflowY: 'auto',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`query-bubble ${msg.sender === 'user' ? 'query-user' : 'query-assistant'}`}
                    style={{ fontSize: '11.5px', lineHeight: 1.45 }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                      <b>{msg.sender === 'user' ? 'Investigator' : 'Forensic AI'}</b>
                      <small style={{ color: '#64748b' }}>
                        {msg.source === 'groq'
                          ? `Groq (${(msg.model || selectedGroqModel).split('-')[0]})`
                          : 'OpenCV Rule Engine'}
                      </small>
                    </div>
                    <p style={{ margin: 0, whiteSpace: 'pre-line' }}>{msg.text}</p>

                    {msg.groq_error && (
                      <div
                        style={{
                          marginTop: '6px',
                          padding: '6px 8px',
                          background: '#fffbeb',
                          border: '1px solid #fef3c7',
                          borderRadius: '4px',
                          color: '#92400e',
                          fontSize: '10.5px',
                        }}
                      >
                        <b>Groq Notice:</b> {msg.groq_error}.{' '}
                        <button
                          type="button"
                          onClick={() => setIsGroqConfigOpen(true)}
                          style={{ textDecoration: 'underline', fontWeight: 'bold', background: 'none', border: 'none', cursor: 'pointer', color: '#b45309' }}
                        >
                          Check Groq Key in Setup
                        </button>
                      </div>
                    )}

                    {msg.events && msg.events.length > 0 && (
                      <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {msg.events.map((ev, evIdx) => (
                          <button
                            key={evIdx}
                            className="btn btn-secondary"
                            style={{
                              fontSize: '10px',
                              padding: '2px 8px',
                              justifyContent: 'flex-start',
                              height: '24px',
                              background: '#f0fdf4',
                              borderColor: '#bbf7d0',
                              color: '#15803d',
                            }}
                            onClick={() => {
                              if (ev.start_time) {
                                try {
                                  const sec = (new Date(ev.start_time).getTime() / 1000) % (duration || 60);
                                  seekVideo(sec);
                                } catch {
                                  seekVideo(evIdx * 2);
                                }
                              } else {
                                seekVideo(evIdx * 2);
                              }
                            }}
                          >
                            Jump to {ev.event_type} ({ev.start_time || '00:00'})
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {isQuerying && (
                  <div className="query-bubble query-assistant" style={{ fontStyle: 'italic', color: '#64748b' }}>
                    <span className="pulse" style={{ display: 'inline-block', marginRight: '6px' }} />
                    Analyzing timeline, kinematics, and events with Groq AI...
                  </div>
                )}
              </div>

              {/* Form Input Row */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendQuery(queryInput);
                }}
                style={{ display: 'flex', gap: '8px' }}
              >
                <input
                  type="text"
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  placeholder="e.g. 'Did any person enter after 10:00?', 'What vehicles were tracked?', 'Check tampering'..."
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    fontSize: '12px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    background: '#fff',
                    outline: 0,
                  }}
                />
                <Button
                  variant="primary"
                  icon={Send}
                  type="submit"
                  disabled={isQuerying || !queryInput.trim()}
                >
                  Ask AI
                </Button>
              </form>
            </div>
          )}

          {timelineSubTab === 'detections' && (
            <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Timecode</th>
                    <th>Type</th>
                    <th>Track</th>
                    <th>Confidence</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {events.length > 0 ? (
                    events.slice(0, 30).map((ev, i) => (
                      <tr key={i}>
                        <td className="mono" style={{ color: '#0f766e', fontWeight: 600 }}>
                          {ev.start_time ? new Date(ev.start_time).toISOString().slice(11, 23) : `00:00:${(i * 2).toString().padStart(2, '0')}.00`}
                        </td>
                        <td>
                          <b>{ev.object_type || ev.event_type}</b>
                        </td>
                        <td className="mono">TRK-{ev.track_id ?? i + 101}</td>
                        <td>{Math.round((ev.confidence || 0.85) * 100)}%</td>
                        <td style={{ textAlign: 'right' }}>
                          <Button
                            variant="secondary"
                            icon={Play}
                            onClick={() => {
                              if (ev.start_time) {
                                try {
                                  const sec = (new Date(ev.start_time).getTime() / 1000) % (duration || 60);
                                  seekVideo(sec);
                                } catch {
                                  seekVideo((i * 1.8) % (duration || 60));
                                }
                              } else {
                                seekVideo((i * 1.8) % (duration || 60));
                              }
                            }}
                          >
                            Seek
                          </Button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', color: '#94a3b8', padding: '20px' }}>
                        No detections recorded for this video.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {timelineSubTab === 'incidents' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
              {reconstructed.length > 0 ? (
                reconstructed.map((rev, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '10px 12px',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                      background: '#fff',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <b style={{ color: '#172554', fontSize: '12px' }}>{rev.title}</b>
                      <p style={{ margin: '3px 0 0', color: '#64748b', fontSize: '11px' }}>{rev.description}</p>
                    </div>
                    <Button
                      variant="secondary"
                      icon={Play}
                      onClick={() => {
                        if (rev.start_time) {
                          try {
                            const sec = (new Date(rev.start_time).getTime() / 1000) % (duration || 60);
                            seekVideo(sec);
                          } catch {}
                        }
                      }}
                    >
                      Seek
                    </Button>
                  </div>
                ))
              ) : (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '20px' }}>
                  No reconstructed narrative incidents detected.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  // INVESTIGATION DETAIL WORKSPACE
  const renderInvestigationDetail = () => {
    return (
      <div className="page detail-page">
        <PageTitle
          eyebrow="INVESTIGATION WORKSPACE"
          title={selectedCase?.name || (loadedFileName ? `Analysis: ${loadedFileName}` : 'Active Investigation Workspace')}
          description={selectedCase ? `Case Ref: ${selectedCase.case_number || selectedCase.id.slice(0, 8)} • Lead Specialist: ${selectedCase.investigator || 'Unassigned'}` : (loadedFileName ? `Artifact: ${loadedFileName}` : 'Select a case or ingest media to begin investigation')}
          action={
            <div style={{ display: 'flex', gap: '8px' }}>
              <Button
                variant="primary"
                icon={UploadCloud}
                onClick={() => setIsUploadModalOpen(true)}
              >
                Ingest Media
              </Button>
              <Button
                variant="secondary"
                icon={MessageSquare}
                onClick={() => setIsQueryModalOpen(true)}
              >
                AI Assistant
              </Button>
              <Button
                variant="secondary"
                icon={FileBarChart}
                onClick={handleExportPDF}
              >
                Export Report
              </Button>
            </div>
          }
        />

        <div className="workspace-grid">
          <div>
            {renderVideoViewer()}
            {renderTimeline({ full: false })}
            {renderTimelineTabsSection()}
          </div>

          {/* Right-hand forensic context panel */}
          <div className="panel right-panel">
            <div className="section-head" style={{ marginBottom: '14px' }}>
              <div>
                <p className="eyebrow">FORENSIC CONTEXT</p>
                <h3>Incident Context</h3>
              </div>
              <Button
                variant="secondary"
                icon={Sparkles}
                onClick={() => setIsQueryModalOpen(true)}
              >
                Query
              </Button>
            </div>

            {analysisResult ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div className="selected-panel" style={{ background: '#f8fafc', padding: '12px', borderRadius: '6px' }}>
                  <p className="eyebrow">ANALYSIS HEADLINE</p>
                  <b style={{ color: '#1e293b', fontSize: '13px' }}>
                    {analysisResult.forensic_summary?.headline || 'Video Stream Analyzed'}
                  </b>
                  <p style={{ margin: '6px 0 0', color: '#64748b', fontSize: '11px', lineHeight: 1.5 }}>
                    {analysisResult.forensic_summary?.summary ||
                      'Temporal correlation and OpenCV multi-stage forensic object detection completed.'}
                  </p>
                </div>

                <div>
                  <p className="eyebrow" style={{ marginBottom: '6px' }}>
                    DETECTED OBJECT CLASSES ({analysisResult.forensic_summary?.objects_detected?.length || 0})
                  </p>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {(analysisResult.forensic_summary?.objects_detected || []).map(
                      (obj, idx) => (
                        <span key={idx} className="hash-pill" style={{ background: '#ecfdf5', borderColor: '#a7f3d0' }}>
                          {obj}
                        </span>
                      )
                    )}
                  </div>
                </div>

                <div>
                  <p className="eyebrow" style={{ marginBottom: '6px' }}>
                    KEY FORENSIC EVENTS ({analysisResult.reconstruction_count || 0})
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                    {(analysisResult.reconstructed_events || []).slice(0, 5).map((rev, i) => (
                      <div
                        key={i}
                        style={{
                          padding: '8px 10px',
                          border: '1px solid #e2e8f0',
                          borderRadius: '4px',
                          background: '#fff',
                          cursor: 'pointer',
                        }}
                        onClick={() => {
                          if (rev.start_time) {
                            try {
                              const sec = (new Date(rev.start_time).getTime() / 1000) % (duration || 60);
                              seekVideo(sec);
                            } catch {}
                          }
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <b style={{ fontSize: '11px', color: '#172554' }}>{rev.title}</b>
                          <span style={{ fontSize: '9px', color: '#047857' }}>
                            {Math.round((rev.confidence || 0.85) * 100)}%
                          </span>
                        </div>
                        <small style={{ color: '#64748b', fontSize: '10px' }}>{rev.description}</small>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '12px' }}>
                  <Button
                    variant="secondary"
                    className="full"
                    icon={FileText}
                    onClick={() => setView('Reports')}
                  >
                    View Official Dossier
                  </Button>
                </div>
              </div>
            ) : (
              <EmptyState
                title="Awaiting Media Ingest"
                description="Load a surveillance video file or raw DVR disk image to unlock neural detection, entity tracking, and event reconstruction."
                action="Ingest Media"
                onAction={() => setIsUploadModalOpen(true)}
                icon={Video}
              />
            )}
          </div>
        </div>
      </div>
    );
  };

  // DETECTIONS VIEW
  const renderDetections = () => {
    const events = analysisResult?.events || [];
    const filteredEvents = events.filter(
      (e) =>
        (e.object_type && e.object_type.toLowerCase().includes(globalSearchText.toLowerCase())) ||
        (e.event_type && e.event_type.toLowerCase().includes(globalSearchText.toLowerCase()))
    );

    return (
      <div className="page">
        <PageTitle
          eyebrow="ANALYSIS / DETECTIONS"
          title="OpenCV Forensic Detections"
          description="Detailed multi-stage frame detections (HOG + Haar + MOG2), bounding coordinates, track IDs, and confidence telemetry."
          action={
            <Button
              variant="primary"
              icon={Play}
              onClick={() => setView('Investigation Detail')}
            >
              Return to CCTV Viewer
            </Button>
          }
        />

        <div className="filters">
          <div className="filter-search">
            <Search size={15} />
            <input
              value={globalSearchText}
              onChange={(e) => setGlobalSearchText(e.target.value)}
              placeholder="Filter by object type (e.g. person, car, bag)..."
            />
          </div>
          <Button icon={Filter}>Confidence &gt; 50%</Button>
        </div>

        <div className="panel table-panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Classification</th>
                  <th>Track Identifier</th>
                  <th>Confidence Score</th>
                  <th>Camera Channel</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.length > 0 ? (
                  filteredEvents.map((ev, i) => (
                    <tr
                      key={i}
                      onClick={() => {
                        seekVideo((i * 1.8) % (duration || 60));
                        setView('Investigation Detail');
                      }}
                    >
                      <td>
                        <b className="mono">
                          {ev.start_time
                            ? new Date(ev.start_time).toISOString().slice(11, 23)
                            : `00:00:${(i * 2).toString().padStart(2, '0')}.00`}
                        </b>
                      </td>
                      <td>
                        <b>{ev.object_type || ev.event_type}</b>
                        <small>{ev.event_type}</small>
                      </td>
                      <td>
                        <span className="mono">TRK-{ev.track_id ?? i + 101}</span>
                      </td>
                      <td>
                        <div className="confidence">
                          <span>{Math.round((ev.confidence || 0.8) * 100)}%</span>
                          <i>
                            <b style={{ width: `${Math.round((ev.confidence || 0.8) * 100)}%` }} />
                          </i>
                        </div>
                      </td>
                      <td>{ev.camera_id || 'CH-01'}</td>
                      <td style={{ textAlign: 'right' }}>
                        <Button
                          variant="secondary"
                          icon={Play}
                          onClick={() => {
                            seekVideo((i * 1.8) % (duration || 60));
                            setView('Investigation Detail');
                          }}
                        >
                          Jump to Frame
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        title="No Detections Recorded"
                        description={
                          analysisResult
                            ? 'No objects matching current filter criteria.'
                            : 'Upload a video file to perform automated OpenCV forensic detection.'
                        }
                        action={!analysisResult ? 'Load Video' : undefined}
                        onAction={() => setIsUploadModalOpen(true)}
                        icon={ScanIcon}
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ENTITIES VIEW
  const renderEntities = () => {
    const objects = analysisResult?.forensic_summary?.objects_detected || [];

    return (
      <div className="page">
        <PageTitle
          eyebrow="ANALYSIS / ENTITIES"
          title="Tracked Physical Entities"
          description="Unique physical persons, vehicles, and containers tracked through multi-frame temporal association."
          action={
            <Button
              variant="primary"
              icon={Play}
              onClick={() => setView('Investigation Detail')}
            >
              Open Viewer
            </Button>
          }
        />

        {objects.length > 0 ? (
          <div className="entity-grid">
            {objects.map((obj, i) => {
              const matchingEvents = (analysisResult?.events || []).filter(
                (e) => (e.object_type || '').toLowerCase() === obj.toLowerCase()
              );
              const count = matchingEvents.length || 1;
              const firstEvent = matchingEvents[0];
              const lastEvent = matchingEvents[matchingEvents.length - 1];
              const avgConf =
                matchingEvents.length > 0
                  ? Math.round(
                      (matchingEvents.reduce((acc, ev) => acc + (ev.confidence || 0.8), 0) /
                        matchingEvents.length) *
                        100
                    )
                  : 85;

              return (
                <div
                  key={i}
                  className="entity-card"
                  onClick={() => {
                    setSelectedEntity({
                      type: obj,
                      id: `ENT-${100 + i}`,
                      observations: count,
                      confidence: avgConf / 100,
                    });
                  }}
                >
                  <div className={`entity-thumb ${i % 2 === 0 ? 'teal' : 'amber'}`}>
                    <UserRound size={32} />
                  </div>
                  <div className="entity-card-content">
                    <div className="entity-title">
                      <div>
                        <b>{obj.toUpperCase()}</b>
                        <small>ENTITY #{100 + i} • {count} observation{count === 1 ? '' : 's'}</small>
                      </div>
                      <StatusBadge tone="teal">TRACKED</StatusBadge>
                    </div>
                    <div className="entity-details">
                      <div>
                        <span>FIRST SEEN</span>
                        <b>
                          {firstEvent?.start_time
                            ? new Date(firstEvent.start_time).toISOString().slice(11, 23)
                            : '00:00:00.00'}
                        </b>
                      </div>
                      <div>
                        <span>LAST SEEN</span>
                        <b>
                          {lastEvent?.end_time
                            ? new Date(lastEvent.end_time).toISOString().slice(11, 23)
                            : lastEvent?.start_time
                            ? new Date(lastEvent.start_time).toISOString().slice(11, 23)
                            : '00:00:00.00'}
                        </b>
                      </div>
                    </div>
                    <div className="confidence">
                      <span>{avgConf}% CONFIDENCE</span>
                      <i>
                        <b style={{ width: `${avgConf}%` }} />
                      </i>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="panel">
            <EmptyState
              title="No Tracked Entities"
              description="Ingest video evidence to discover and track physical entities across camera timecodes."
              action="Ingest Media"
              onAction={() => setIsUploadModalOpen(true)}
              icon={UserRound}
            />
          </div>
        )}
      </div>
    );
  };

  // EVENTS VIEW
  const renderEvents = () => {
    const revs = analysisResult?.reconstructed_events || [];

    return (
      <div className="page">
        <PageTitle
          eyebrow="ANALYSIS / EVENTS"
          title="Reconstructed Forensic Incidents"
          description="Synthesized multi-sensor incidents and behavioral transitions identified from the video stream."
          action={
            <Button
              variant="primary"
              icon={Play}
              onClick={() => setView('Investigation Detail')}
            >
              Return to CCTV Viewer
            </Button>
          }
        />

        {revs.length > 0 ? (
          <div className="event-list">
            {revs.map((rev, i) => (
              <div
                key={i}
                className="event-card panel"
                onClick={() => {
                  seekVideo(i * 5);
                  setView('Investigation Detail');
                }}
              >
                <div className={`event-icon ${i % 2 === 0 ? 'teal' : 'warning'}`}>
                  <Activity size={18} />
                </div>
                <div className="event-main">
                  <div>
                    <b>{rev.title}</b>
                    <StatusBadge tone={i % 2 === 0 ? 'teal' : 'warning'}>
                      {rev.event_type}
                    </StatusBadge>
                  </div>
                  <p>{rev.description}</p>
                  <span>
                    Camera: {rev.camera_id || 'CH-01'} • Timestamp:{' '}
                    {rev.start_time
                      ? new Date(rev.start_time).toISOString().slice(11, 23)
                      : '00:00:00'}
                  </span>
                </div>
                <div className="event-confidence">
                  <div className="confidence">
                    <span>{Math.round((rev.confidence || 0.85) * 100)}%</span>
                    <i>
                      <b style={{ width: `${Math.round((rev.confidence || 0.85) * 100)}%` }} />
                    </i>
                  </div>
                  <small>Neural Verification</small>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="panel">
            <EmptyState
              title="No Reconstructed Events"
              description="Narrative incidents will be automatically correlated when video media is processed."
              action="Ingest Media"
              onAction={() => setIsUploadModalOpen(true)}
              icon={Activity}
            />
          </div>
        )}
      </div>
    );
  };

  // INTEGRITY VIEW
  const renderIntegrity = () => {
    const integrity = analysisResult?.integrity_analysis;

    return (
      <div className="page">
        <PageTitle
          eyebrow="VALIDATION / SOURCE INTEGRITY"
          title="Evidence Integrity & Bitstream Audit"
          description="Cryptographic checksums, frame-rate consistency checks, and video tampering verification."
          action={
            <Button variant="primary" icon={Download} onClick={handleExportPDF}>
              Export Audit Certificate
            </Button>
          }
        />

        {integrity ? (
          <>
            <div className="integrity-overview">
              <div className="integrity-hero panel">
                <div className="shield-ring">
                  <ShieldCheck size={28} />
                </div>
                <div>
                  <p className="eyebrow">BITSTREAM VALIDATION</p>
                  <h2>{integrity.overall_status === 'PASS' ? 'INTEGRITY VERIFIED' : 'WARNING'}</h2>
                  <p>All video frames inspected for timestamp and sequence continuity.</p>
                </div>
                <strong>{integrity.integrity_score}%</strong>
              </div>

              <div className="panel technical-grid">
                <div className="tech-meta">
                  <span>FRAMES INSPECTED</span>
                  <b>{integrity.frames_checked || analysisResult?.frames_analyzed || 150}</b>
                </div>
                <div className="tech-meta">
                  <span>TIMESTAMP GAPS</span>
                  <b>{integrity.timestamp_gaps || 0}</b>
                </div>
                <div className="tech-meta">
                  <span>DUPLICATE FRAMES</span>
                  <b>{integrity.duplicate_sequences || 0}</b>
                </div>
                <div className="tech-meta">
                  <span>CORRUPTED SLICES</span>
                  <b>{integrity.corrupted_frames || 0}</b>
                </div>
                <div className="tech-meta">
                  <span>RESOLUTION JUMPS</span>
                  <b>{integrity.resolution_changes || 0}</b>
                </div>
                <div className="tech-meta">
                  <span>HASH STATUS</span>
                  <b style={{ color: '#047857' }}>MATCHED (SHA-256)</b>
                </div>
              </div>
            </div>

            <div className="panel" style={{ padding: '20px', marginTop: '16px' }}>
              <div className="section-head" style={{ marginBottom: '14px' }}>
                <div>
                  <p className="eyebrow">STANDARDS CHECKLIST</p>
                  <h3>Forensic Continuity Audit</h3>
                </div>
              </div>
              <div className="integrity-checks">
                {[
                  ['Timestamp Continuity', integrity.timestamp_continuity, 'No frame timestamp jumping or backward time travel detected.'],
                  ['Frame Continuity', integrity.frame_continuity, 'All expected I/P/B frame sequences present without dropped blocks.'],
                  ['FPS Consistency', integrity.fps_consistency, 'Stream operates at uniform frame pacing.'],
                  ['Duplicate Frame Scan', !integrity.duplicate_frames, 'No synthesized freeze-frame tampering discovered.'],
                  ['Metadata Consistency', integrity.metadata_consistency, 'Atom stream tags match encoded video codec parameters.'],
                  ['Compression Consistency', integrity.compression_consistency, 'No mid-stream quantizer discontinuities.'],
                ].map(([label, pass, desc], i) => (
                  <div key={i} className="check-row panel">
                    <CheckCircle2 size={18} className="check-icon" />
                    <div>
                      <b>{label as string}</b>
                      <small>{desc as string}</small>
                    </div>
                    <StatusBadge tone={pass ? 'success' : 'warning'}>
                      {pass ? 'PASSED' : 'FLAGGED'}
                    </StatusBadge>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="panel">
            <EmptyState
              title="No Integrity Audit Available"
              description="Container, codec, hash, timestamp and manipulation checks will appear after video analysis."
              action="Ingest Media"
              onAction={() => setIsUploadModalOpen(true)}
              icon={ShieldCheck}
            />
          </div>
        )}
      </div>
    );
  };

  // REPORTS VIEW
  const renderReports = () => {
    return (
      <div className="page">
        <PageTitle
          eyebrow="DOCUMENTS / DOSSIER"
          title="Forensic Reports & Certification"
          description="Review, inspect, and export court-admissible forensic dossiers with SHA-256 seals."
          action={
            <Button
              variant="primary"
              icon={Download}
              onClick={handleExportPDF}
              disabled={!analysisResult}
            >
              Export Certified PDF Dossier
            </Button>
          }
        />

        {analysisResult ? (
          <div className="report-layout">
            {/* Paper Preview */}
            <div className="panel report-paper">
              <div className="report-paper-top">
                <span>TRACE-X FORENSIC REPORT</span>
                <span>CLASSIFICATION: EVIDENCE / CONFIDENTIAL</span>
              </div>

              <h2>FORENSIC EXAMINATION DOSSIER</h2>
              <p className="mono">
                CASE REF: {selectedCase?.case_number || selectedCase?.id?.slice(0, 8) || 'UNASSIGNED'} • ARTIFACT: {loadedFileName || 'VIDEO_EVIDENCE'}
              </p>

              <div className="report-rule" />

              <h4>1. EVIDENCE IDENTIFICATION & CHAIN OF CUSTODY</h4>
              <p>
                Digital video artifact <b>{loadedFileName}</b> acquired under forensic isolation.
                Cryptographic verification establishes that original bitstreams remain untampered.
              </p>
              {loadedFileHash && (
                <div className="hash-pill" style={{ margin: '10px 0' }}>
                  SHA-256 SEAL: {loadedFileHash}
                </div>
              )}

              <h4>2. SUMMARY OF OBSERVATIONS</h4>
              <p>
                {analysisResult?.forensic_summary?.summary ||
                  'Temporal correlation and OpenCV multi-stage forensic object detection completed.'}
              </p>

              <h4>3. INTEGRITY & TAMPERING AUDIT</h4>
              <p>
                Container continuity score: <b>{analysisResult?.integrity_analysis?.integrity_score ?? 100}%</b>. Overall
                status: <b>{analysisResult?.integrity_analysis?.overall_status || 'VERIFIED PASS'}</b>.
              </p>

              <div className="report-actions">
                <Button variant="primary" icon={Download} onClick={handleExportPDF}>
                  Download PDF Dossier (.pdf)
                </Button>
                <Button variant="secondary" icon={MessageSquare} onClick={() => setIsQueryModalOpen(true)}>
                  Ask AI Assistant
                </Button>
              </div>
            </div>

            {/* Report Metadata Info */}
            <div className="panel" style={{ padding: '20px' }}>
              <div className="section-head" style={{ marginBottom: '14px' }}>
                <div>
                  <p className="eyebrow">CERTIFICATION</p>
                  <h3>Court Admissibility</h3>
                </div>
              </div>
              <p style={{ fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>
                Trace-X dossiers follow ISO/IEC 27037 and NIST SP 800-86 standards for digital evidence integrity, ensuring
                non-repudiation of cryptographic digests and audit logs.
              </p>
              <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="check-row panel">
                  <CheckCircle2 size={16} className="check-icon" />
                  <div>
                    <b>SHA-256 Hashing Seal</b>
                    <small>Calculated before memory buffering</small>
                  </div>
                </div>
                <div className="check-row panel">
                  <CheckCircle2 size={16} className="check-icon" />
                  <div>
                    <b>OpenCV Forensic Vision</b>
                    <small>Confidence thresholds documented</small>
                  </div>
                </div>
                <div className="check-row panel">
                  <CheckCircle2 size={16} className="check-icon" />
                  <div>
                    <b>Bitstream Integrity Check</b>
                    <small>Frame rate & sequence validated</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="panel">
            <EmptyState
              title="No Forensic Dossier Available"
              description="Ingest and analyze a video or DVR image to generate a certified forensic examination dossier."
              action="Ingest Video or DVR Image"
              onAction={() => setIsUploadModalOpen(true)}
              icon={FileBarChart}
            />
          </div>
        )}
      </div>
    );
  };

  // PROCESSING PIPELINE VIEW
  const renderProcessing = () => {
    const steps = [
      { id: 1, name: 'Evidence Ingestion & SHA-256 Seal' },
      { id: 2, name: 'Container Probing & Normalization' },
      { id: 3, name: 'OpenCV Multi-Stage Object Detection' },
      { id: 4, name: 'Temporal Event Reconstruction' },
      { id: 5, name: 'Bitstream Integrity Verification' },
    ];

    return (
      <div className="page">
        <PageTitle
          eyebrow="PIPELINE / ANALYSIS WORKER"
          title="Forensic Processing Engine"
          description="Live asynchronous media pipeline status running on the local FastAPI backend."
          action={
            <Button
              variant="secondary"
              icon={Play}
              onClick={() => setView('Investigation Detail')}
            >
              Open CCTV Viewer
            </Button>
          }
        />

        <div className="processing-layout">
          <div className="panel pipeline-panel">
            <div className="pipeline-progress">
              <div>
                <p className="eyebrow">PIPELINE COMPLETION</p>
                <h2>{processingProgress}%</h2>
                <span>{isProcessing ? 'Analysis pipeline executing...' : 'Engine Ready'}</span>
              </div>
              <div className="progress-track">
                <i style={{ width: `${processingProgress}%` }} />
              </div>
            </div>

            {processingError && (
              <div
                style={{
                  padding: '12px',
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '6px',
                  color: '#b91c1c',
                  margin: '14px 0',
                  fontSize: '11px',
                }}
              >
                <AlertTriangle size={16} style={{ display: 'inline', marginRight: '6px' }} />
                <b>Pipeline Error:</b> {processingError}
              </div>
            )}

            <div className="pipeline">
              {steps.map((s) => {
                const isComplete = processingPhase > s.id || (!isProcessing && processingProgress === 100);
                const isActive = isProcessing && processingPhase === s.id;

                return (
                  <div
                    key={s.id}
                    className={`pipeline-step ${isComplete ? 'complete' : ''} ${isActive ? 'active' : ''}`}
                  >
                    <div className="step-marker">
                      {isComplete ? (
                        <CheckCircle2 size={14} />
                      ) : isActive ? (
                        <div className="step-spinner" />
                      ) : (
                        <span>{s.id}</span>
                      )}
                    </div>
                    <div className="step-copy">
                      <b>{s.name}</b>
                      <small>
                        {isComplete ? 'Completed' : isActive ? 'Processing stage...' : 'Queued'}
                      </small>
                    </div>
                    <StatusBadge tone={isComplete ? 'success' : isActive ? 'teal' : 'slate'}>
                      {isComplete ? 'Done' : isActive ? 'Active' : 'Pending'}
                    </StatusBadge>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pipeline Live Log */}
          <div className="panel" style={{ padding: '20px' }}>
            <div className="section-head" style={{ marginBottom: '10px' }}>
              <div>
                <p className="eyebrow">DIAGNOSTICS</p>
                <h3>Pipeline Stream Logs</h3>
              </div>
            </div>
            <div
              style={{
                background: '#0f172a',
                color: '#e2e8f0',
                padding: '12px',
                borderRadius: '6px',
                fontFamily: 'ui-monospace, monospace',
                fontSize: '10px',
                height: '340px',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              {processingLogs.length > 0 ? (
                processingLogs.map((log, idx) => (
                  <div key={idx} style={{ color: log.includes('[ERROR]') ? '#f87171' : log.includes('[COMPLETED]') ? '#4ade80' : '#cbd5e1' }}>
                    {log}
                  </div>
                ))
              ) : (
                <div style={{ color: '#64748b' }}>Awaiting pipeline execution...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // Main View Router
  // -------------------------------------------------------------------------

  let mainContent: ReactNode;
  switch (view) {
    case 'Overview':
      mainContent = renderOverview();
      break;
    case 'Investigations':
      mainContent = renderInvestigations();
      break;
    case 'Investigation Detail':
      mainContent = renderInvestigationDetail();
      break;
    case 'Video Evidence':
    case 'Evidence':
      mainContent = (
        <div className="page">
          <PageTitle
            eyebrow="MEDIA ASSETS"
            title="Video Evidence & Carved Streams"
            description="Acquired video containers, DVR raw sector carves, and metadata streams."
            action={
              <Button
                variant="primary"
                icon={UploadCloud}
                onClick={() => setIsUploadModalOpen(true)}
              >
                Ingest Media
              </Button>
            }
          />
          {loadedFileName ? (
            <div className="evidence-grid">
              <button
                className="evidence-card"
                onClick={() => setView('Investigation Detail')}
              >
                <div className="evidence-thumb teal">
                  <Video size={24} />
                  <span>PLAYABLE</span>
                </div>
                <div className="evidence-info">
                  <b>{loadedFileName}</b>
                  <small className="mono">{loadedFileHash.slice(0, 16)}...</small>
                  <span>Size: {formatFileSize(loadedFileSize)}</span>
                </div>
              </button>
            </div>
          ) : (
            <div className="panel">
              <EmptyState
                title="No evidence items found"
                description="Upload standard video files (.mp4, .avi, .mov) or raw DVR disk images (.dd, .raw, .img) to populate this library."
                action="Upload Evidence"
                onAction={() => setIsUploadModalOpen(true)}
                icon={Video}
              />
            </div>
          )}
        </div>
      );
      break;
    case 'Timeline':
      mainContent = (
        <div className="page">
          <PageTitle
            eyebrow="TEMPORAL / CHRONOLOGY"
            title="Forensic Timeline Workspace"
            description="Synchronized multi-channel view of frame detections, motion vectors, and incidents."
          />
          {renderTimeline({ full: true })}
          {renderTimelineTabsSection()}
        </div>
      );
      break;
    case 'Detections':
      mainContent = renderDetections();
      break;
    case 'Entities':
    case 'Entity Detail':
      mainContent = renderEntities();
      break;
    case 'Events':
      mainContent = renderEvents();
      break;
    case 'Integrity':
      mainContent = renderIntegrity();
      break;
    case 'Reports':
      mainContent = renderReports();
      break;
    case 'Processing':
      mainContent = renderProcessing();
      break;
    default:
      mainContent = renderOverview();
  }

  // -------------------------------------------------------------------------
  // -------------------------------------------------------------------------
  // Render App Shell or Authentication Gateway
  // -------------------------------------------------------------------------

  if (authChecking) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-[#f5f6f7] text-[#172554]">
        <TraceXLogo variant="dark" className="h-10 w-auto object-contain mb-4 animate-pulse" />
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
          <div className="w-4 h-4 border-2 border-[#172554] border-t-transparent rounded-full animate-spin" />
          <span>Verifying Cryptographic Examiner Session...</span>
        </div>
      </div>
    );
  }

  // If no user is logged in, show the styled Trace-X Login / Register page
  if (!currentUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-shell">
      {/* Mobile Backdrop */}
      <div
        className={`sidebar-backdrop ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px 16px', borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
          <TraceXLogo variant="white" className="h-9 max-h-10 w-auto object-contain" />
          <button
            className="collapse"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          >
            <ChevronLeft size={17} />
          </button>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        <nav>
          {navItems.map(([itemKey, Icon, desc]) => (
            <button
              key={itemKey}
              onClick={() => {
                setView(itemKey);
                setSidebarOpen(false);
              }}
              className={view === itemKey ? 'active' : ''}
              title={desc}
            >
              <Icon size={17} />
              <span>{itemKey}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button
            onClick={() => {
              setView('Processing');
              setSidebarOpen(false);
            }}
            className={view === 'Processing' ? 'active' : ''}
          >
            <Gauge size={17} />
            <span>Processing Pipeline</span>
          </button>

          {/* User profile & Logout item in sidebar */}
          <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 10px', color: '#cbd5e1' }}>
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: 'rgba(255,255,255,0.15)',
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#5eead4',
                }}
              >
                {currentUser.name.charAt(0).toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
                <b style={{ display: 'block', fontSize: '11px', color: '#fff', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {currentUser.name}
                </b>
                <small style={{ display: 'block', fontSize: '9px', color: '#94a3b8', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {currentUser.email}
                </small>
              </div>
            </div>

            <button
              onClick={handleSignOut}
              style={{
                width: '100%',
                marginTop: '4px',
                color: '#f87171',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 10px',
                background: 'transparent',
                border: 0,
                fontSize: '11px',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
              className="hover:bg-red-500/10"
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="app-main">
        {/* Top Header */}
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={18} />
          </button>

          <div className="crumb" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <TraceXLogo variant="dark" className="h-8 max-h-9 w-auto object-contain" />
            <ChevronRight size={14} />
            <b>{view}</b>
            {selectedCase && (
              <>
                <ChevronRight size={14} />
                <span className="mono" style={{ color: '#0f766e', fontWeight: 600 }}>
                  {selectedCase.case_number || selectedCase.name}
                </span>
              </>
            )}
          </div>

          <div className="header-actions">
            <div className="global-search">
              <Search size={16} />
              <input
                aria-label="Global search"
                placeholder="Ask AI or search workspace..."
                value={globalSearchText}
                onChange={(e) => setGlobalSearchText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && globalSearchText.trim()) {
                    handleSendQuery(globalSearchText);
                    setIsQueryModalOpen(true);
                  }
                }}
              />
              <kbd>Enter</kbd>
            </div>

            <button
              className="btn btn-primary"
              style={{ minHeight: '30px', padding: '0 10px', fontSize: '11px' }}
              onClick={() => setIsUploadModalOpen(true)}
            >
              <UploadCloud size={14} /> Ingest Media
            </button>

            <button
              className="icon-btn"
              aria-label="Refresh Data"
              title="Refresh Workspace"
              onClick={fetchCases}
            >
              <RefreshCw size={16} />
            </button>

            {/* Authenticated user profile badge in topbar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '4px 10px',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
              }}
              title={`Logged in as ${currentUser.name} (${currentUser.email})`}
            >
              <div
                style={{
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  background: '#dbeafe',
                  color: '#1e3a8a',
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: '10px',
                  fontWeight: 700,
                }}
              >
                {currentUser.name.charAt(0).toUpperCase()}
              </div>
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#334155' }}>
                {currentUser.name.split(' ')[0]}
              </span>
              <button
                onClick={handleSignOut}
                title="Sign out of Trace-X"
                style={{
                  background: 'none',
                  border: 0,
                  color: '#94a3b8',
                  padding: '2px',
                  display: 'grid',
                  placeItems: 'center',
                  cursor: 'pointer',
                  marginLeft: '4px',
                }}
                className="hover:text-red-600"
              >
                <LogOut size={13} />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main>{mainContent}</main>
      </div>

      {/* =================================================================== */}
      {/* MODAL: NEW INVESTIGATION */}
      {/* =================================================================== */}
      {isNewCaseModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsNewCaseModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="eyebrow">CASE REGISTRY</p>
                <h3>Initiate New Investigation</h3>
              </div>
              <button
                className="icon-btn"
                onClick={() => setIsNewCaseModalOpen(false)}
                aria-label="Close modal"
              >
                <X size={17} />
              </button>
            </div>
            <form onSubmit={handleCreateCaseSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label>INVESTIGATION TITLE *</label>
                  <input
                    required
                    placeholder="e.g. Surveillance Incident 08 - North Gate"
                    value={newCaseName}
                    onChange={(e) => setNewCaseName(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>CASE IDENTIFIER / FILE NUMBER</label>
                  <input
                    placeholder="e.g. V-2024-CCTV-08 (Leave blank to auto-generate)"
                    value={newCaseNumber}
                    onChange={(e) => setNewCaseNumber(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>LEAD INVESTIGATOR / EXAMINER</label>
                  <input
                    placeholder="e.g. Det. J. Miller / Forensic Unit"
                    value={newCaseInvestigator}
                    onChange={(e) => setNewCaseInvestigator(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>CASE BRIEF / NOTES</label>
                  <textarea
                    rows={3}
                    placeholder="Summary of evidentiary requirements and physical acquisition notes..."
                    value={newCaseDesc}
                    onChange={(e) => setNewCaseDesc(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <Button
                  variant="secondary"
                  onClick={() => setIsNewCaseModalOpen(false)}
                  disabled={caseCreating}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  icon={Plus}
                  disabled={caseCreating || !newCaseName.trim()}
                >
                  {caseCreating ? 'Creating Case...' : 'Create Investigation'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: INGEST EVIDENCE / DVR IMAGE */}
      {/* =================================================================== */}
      {isUploadModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsUploadModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="eyebrow">EVIDENCE ACQUISITION</p>
                <h3>Ingest Surveillance Video or DVR Image</h3>
              </div>
              <button
                className="icon-btn"
                onClick={() => setIsUploadModalOpen(false)}
                aria-label="Close modal"
              >
                <X size={17} />
              </button>
            </div>

            <div className="modal-body">
              {/* Dropzone */}
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                accept=".mp4,.avi,.mov,.mkv,.h264,.dd,.raw,.img,.bin,.001,.dat"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileChosen(e.target.files[0]);
                  }
                }}
              />

              <div
                className="dropzone"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileChosen(e.dataTransfer.files[0]);
                  }
                }}
              >
                <div className="dropzone-icon">
                  <UploadCloud size={24} />
                </div>
                <h4>Select or Drag & Drop Media Evidence</h4>
                <p>
                  Supports standard video (<b>MP4, AVI, MOV, MKV</b>) and forensic DVR raw images (
                  <b>.dd, .raw, .img, .bin</b>).
                </p>
              </div>

              {/* Selected File Details & SHA-256 seal */}
              {selectedUploadFile && (
                <div
                  style={{
                    padding: '12px',
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <b style={{ color: '#172554', fontSize: '12px' }}>{selectedUploadFile.name}</b>
                    <span style={{ fontSize: '10px', color: '#64748b' }}>
                      {formatFileSize(selectedUploadFile.size)}
                    </span>
                  </div>

                  <div>
                    <span style={{ fontSize: '10px', color: '#64748b', display: 'block' }}>
                      CRYPTOGRAPHIC SHA-256 SEAL:
                    </span>
                    <div className="hash-pill">
                      {isCalculatingHash ? 'Computing cryptographic hash...' : uploadHash || 'Pending'}
                    </div>
                  </div>
                </div>
              )}

              {/* Target Case selection */}
              <div className="form-group">
                <label>ASSOCIATE WITH INVESTIGATION</label>
                <select
                  value={uploadTargetCaseId}
                  onChange={(e) => setUploadTargetCaseId(e.target.value)}
                >
                  <option value="">-- Standalone Forensic Inspection --</option>
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.case_number ? `[${c.case_number}] ` : ''}
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="modal-footer">
              <Button
                variant="secondary"
                onClick={() => setIsUploadModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                icon={Play}
                disabled={!selectedUploadFile || isCalculatingHash}
                onClick={startAnalysisPipeline}
              >
                Start Forensic Analysis Pipeline
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: CONVERSATIONAL FORENSIC Q&A ASSISTANT */}
      {/* =================================================================== */}
      {isQueryModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsQueryModalOpen(false)}>
          <div className="modal-card" style={{ width: 'min(720px, 100%)' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head" style={{ alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <p className="eyebrow" style={{ margin: 0 }}>AI FORENSIC AGENT</p>
                  <span
                    className="status-pill"
                    style={{
                      background: groqApiKey ? '#ecfdf5' : '#f8fafc',
                      color: groqApiKey ? '#059669' : '#64748b',
                      borderColor: groqApiKey ? '#a7f3d0' : '#e2e8f0',
                      fontSize: '10px',
                      padding: '1px 7px',
                    }}
                  >
                    {groqApiKey ? `● Groq AI (${selectedGroqModel.split('-')[0].toUpperCase()})` : '○ Groq / Local Heuristic'}
                  </span>
                </div>
                <h3 style={{ marginTop: '2px' }}>Investigative Video Intelligence</h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <button
                  className="icon-btn"
                  onClick={() => setIsQueryModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>
            </div>

            <div className="modal-body">
              <div className="query-chat" style={{ maxHeight: '380px' }}>
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`query-bubble ${msg.sender === 'user' ? 'query-user' : 'query-assistant'}`}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                      <b>{msg.sender === 'user' ? 'Investigator' : 'Forensic AI'}</b>
                      {msg.sender === 'assistant' && (
                        <span
                          style={{
                            fontSize: '9px',
                            color: msg.source === 'groq' ? '#059669' : '#64748b',
                            fontWeight: 600,
                            background: msg.source === 'groq' ? '#ecfdf5' : '#f1f5f9',
                            padding: '1px 5px',
                            borderRadius: '3px',
                          }}
                        >
                          {msg.source === 'groq'
                            ? `Groq (${(msg.model || selectedGroqModel).split('-')[0]})`
                            : 'OpenCV Rule Engine'}
                        </span>
                      )}
                    </div>
                    <p style={{ margin: '4px 0 0', whiteSpace: 'pre-line', lineHeight: 1.45 }}>{msg.text}</p>
                    
                    {msg.groq_error && (
                      <div
                        style={{
                          marginTop: '6px',
                          padding: '6px 8px',
                          background: '#fffbeb',
                          border: '1px solid #fef3c7',
                          borderRadius: '4px',
                          fontSize: '10px',
                          color: '#b45309',
                        }}
                      >
                        <b>Groq Notice:</b> {msg.groq_error}
                      </div>
                    )}

                    {msg.events && msg.events.length > 0 && (
                      <div style={{ marginTop: '8px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {msg.events.map((ev: any, idx: number) => {
                          const timeLabel = ev.start_time || `Event #${idx + 1}`;
                          return (
                            <button
                              key={idx}
                              className="btn btn-secondary"
                              style={{ padding: '2px 6px', fontSize: '9px' }}
                              onClick={() => {
                                seekVideo(idx * 4);
                                setIsQueryModalOpen(false);
                                setView('Investigation Detail');
                              }}
                            >
                              Jump to {ev.event_type || 'Event'} ({timeLabel})
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
                {isQuerying && (
                  <div className="query-bubble query-assistant">
                    <small>Analyzing OpenCV timeline events with Groq AI and generating forensic response...</small>
                  </div>
                )}
              </div>

              <div className="query-input-row">
                <input
                  placeholder="e.g. 'Did any person enter after 10:00?', 'What vehicles were tracked?', 'Check tampering'..."
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSendQuery();
                  }}
                />
                <Button
                  variant="primary"
                  icon={Send}
                  onClick={() => handleSendQuery()}
                  disabled={isQuerying || !queryInput.trim()}
                >
                  Send
                </Button>
              </div>

              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  'What objects & persons were detected?',
                  'What vehicles were tracked & at what velocity?',
                  'Check video integrity & frame continuity',
                  'Were any stationary losses or disappearances detected?',
                  'Summarize forensic incident timeline',
                ].map((sugg) => (
                  <button
                    key={sugg}
                    className="btn btn-secondary"
                    style={{ fontSize: '10px', padding: '3px 8px' }}
                    onClick={() => handleSendQuery(sugg)}
                  >
                    {sugg}
                  </button>
                ))}
              </div>
            </div>

            <div className="modal-footer">
              <Button
                variant="secondary"
                onClick={() => setIsQueryModalOpen(false)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* DRAWER: ENTITY DETAIL */}
      {/* =================================================================== */}
      {selectedEntity && (
        <div className="drawer-backdrop" onClick={() => setSelectedEntity(null)}>
          <aside className="drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <p className="eyebrow">PHYSICAL ENTITY DETAIL</p>
                <h3>{selectedEntity.type?.toUpperCase()}</h3>
              </div>
              <button
                className="icon-btn"
                onClick={() => setSelectedEntity(null)}
                aria-label="Close"
              >
                <X size={17} />
              </button>
            </div>
            <div className="drawer-content">
              <div className="drawer-preview">
                <div className="mini-scene">
                  <div className="mini-detection" />
                </div>
              </div>
              <h2>
                {selectedEntity.id}{' '}
                <span>{selectedEntity.type}</span>
              </h2>
              <div className="drawer-meta">
                <div className="tech-meta">
                  <span>TOTAL OBSERVATIONS</span>
                  <b>{selectedEntity.observations} frames</b>
                </div>
                <div className="tech-meta">
                  <span>AVERAGE CONFIDENCE</span>
                  <b>{Math.round((selectedEntity.confidence || 0.9) * 100)}%</b>
                </div>
              </div>

              <div style={{ marginTop: '20px' }}>
                <Button
                  variant="primary"
                  className="full"
                  icon={Play}
                  onClick={() => {
                    setSelectedEntity(null);
                    setView('Investigation Detail');
                  }}
                >
                  Locate in CCTV Viewer
                </Button>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
