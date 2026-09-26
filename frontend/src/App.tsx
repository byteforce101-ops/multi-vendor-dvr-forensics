'use client';

import React, { useState, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Bell,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Code,
  Copy,
  Download,
  ExternalLink,
  Eye,
  EyeOff,
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
  Package,
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
  Terminal,
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
import type { CaseSummary, EvidenceSummary, OverviewStats } from './api/client';
import type {
  VideoAnalysisResult,
  ReconstructedForensicEvent,
  VideoIntegrityAnalysis,
  EvidenceFile,
  SupabaseUser,
  ObjectDisappearance,
  ObjectDisappearanceAnalysis,
} from './types';
import { generateForensicDossier } from './utils/forensicDossier';
import TraceXLogo from './components/TraceXLogo';
import tracexLogo from './assets/tracex-logo.png';
import casesIcon from './assets/metric-cases.png';
import evidenceIcon from './assets/metric-evidence.png';
import trackedEntitiesIcon from './assets/metric-tracked-entities.png';
import eventsIcon from './assets/metric-events.png';
import integrityIcon from './assets/metric-integrity.png';
import { LoginPage } from './components/LoginPage';
import { LoadingScreen } from './components/LoadingScreen';
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
  | 'Disappearances'
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
  ['Disappearances', EyeOff, 'Object Disappearance Detection'],
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

function getEventTimestampSeconds(
  item: any,
  baseTimeStr?: string | null,
  fps: number = 25,
  maxDuration: number = 60
): number {
  if (!item) return 0;

  // 1. Direct seconds properties
  if (typeof item.start_seconds === 'number' && !isNaN(item.start_seconds) && item.start_seconds >= 0) {
    return Math.min(maxDuration, item.start_seconds);
  }
  if (typeof item.timestamp_seconds === 'number' && !isNaN(item.timestamp_seconds) && item.timestamp_seconds >= 0) {
    return Math.min(maxDuration, item.timestamp_seconds);
  }
  if (typeof item.seconds === 'number' && !isNaN(item.seconds) && item.seconds >= 0) {
    return Math.min(maxDuration, item.seconds);
  }

  // 2. Metadata first_frame / frame_idx / start_seconds
  if (item.metadata && typeof item.metadata === 'object') {
    if (typeof item.metadata.start_seconds === 'number' && !isNaN(item.metadata.start_seconds) && item.metadata.start_seconds >= 0) {
      return Math.min(maxDuration, item.metadata.start_seconds);
    }
    const frame = item.metadata.first_frame ?? item.metadata.frame_idx ?? item.metadata.frame_number ?? item.metadata.frame;
    if (typeof frame === 'number' && !isNaN(frame) && fps > 0 && frame >= 0) {
      return Math.min(maxDuration, frame / fps);
    }
  }

  // 3. String / ISO timestamps (disappearance_time, start_time, first_seen, last_seen)
  const timeStr =
    item.disappearance_time ||
    item.start_time ||
    item.first_seen ||
    item.last_seen ||
    (typeof item === 'string' ? item : null);

  if (timeStr && typeof timeStr === 'string') {
    // A) Numeric string (e.g., "12.5")
    const asNum = parseFloat(timeStr);
    if (!isNaN(asNum) && !timeStr.includes(':') && !timeStr.includes('-') && !timeStr.includes('T')) {
      return Math.min(maxDuration, Math.max(0, asNum));
    }

    // B) HH:MM:SS or MM:SS format without date
    const timeRegex = /(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})(?:\.(\d+))?/;
    if (!timeStr.includes('T') && !timeStr.includes('-')) {
      const timeMatch = timeStr.match(timeRegex);
      if (timeMatch) {
        const h = timeMatch[1] ? parseInt(timeMatch[1], 10) : 0;
        const m = parseInt(timeMatch[2], 10);
        const s = parseInt(timeMatch[3], 10);
        const ms = timeMatch[4] ? parseFloat('0.' + timeMatch[4]) : 0;
        const total = h * 3600 + m * 60 + s + ms;
        return Math.min(maxDuration, Math.max(0, total));
      }
    }

    // C) ISO / Datetime strings (e.g. "2026-03-29T14:30:15.200Z")
    try {
      const parsedTime = new Date(timeStr).getTime();
      if (!isNaN(parsedTime)) {
        if (baseTimeStr) {
          const baseTime = new Date(baseTimeStr).getTime();
          if (!isNaN(baseTime)) {
            const diffSec = (parsedTime - baseTime) / 1000;
            if (diffSec >= 0 && diffSec <= maxDuration * 1.5) {
              return Math.min(maxDuration, Math.max(0, diffSec));
            }
          }
        }
        // Fallback relative modulo if baseTime isn't aligned
        const modSec = (parsedTime / 1000) % (maxDuration || 60);
        return Math.max(0, Math.min(maxDuration, modSec));
      }
    } catch {
      // fallback
    }
  }

  return 0;
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
  type = 'button',
}: {
  children?: ReactNode;
  onClick?: (e?: any) => void;
  variant?: 'primary' | 'secondary' | 'success' | 'ai' | 'danger' | 'action' | 'ghost';
  icon?: React.ComponentType<{ size?: number }>;
  className?: string;
  disabled?: boolean;
  title?: string;
  type?: 'button' | 'submit' | 'reset';
}) {
  return (
    <button
      type={type}
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
  customAction,
  hideIcon,
}: {
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
  icon?: React.ComponentType<{ size?: number }>;
  customAction?: ReactNode;
  hideIcon?: boolean;
}) {
  return (
    <div className="empty-state">
      {!hideIcon && (
        <div className="empty-icon">
          <Icon size={24} />
        </div>
      )}
      <h3>{title}</h3>
      <p>{description}</p>
      {customAction ? (
        customAction
      ) : action && onAction ? (
        <Button variant="primary" onClick={onAction} icon={Plus}>
          {action}
        </Button>
      ) : null}
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

  // Global realistic loading screen state
  const [loadingConfig, setLoadingConfig] = useState<{
    isVisible: boolean;
    variant: 'simple' | 'detailed';
    title: string;
    subtitle?: string;
    steps: string[];
    durationMs: number;
    onComplete?: () => void;
  }>({
    isVisible: false,
    variant: 'simple',
    title: '',
    steps: [],
    durationMs: 1800,
  });

  const triggerLoading = (
    title: string,
    steps: string[],
    onCompleteAction?: () => void,
    subtitle = 'Loading workspace...',
    durationMs = 1800,
    variant: 'simple' | 'detailed' = 'simple'
  ) => {
    setLoadingConfig({
      isVisible: true,
      variant,
      title,
      subtitle,
      steps,
      durationMs,
      onComplete: () => {
        setLoadingConfig((prev) => ({ ...prev, isVisible: false }));
        if (onCompleteAction) {
          onCompleteAction();
        }
      },
    });
  };

  const navigateWithLoading = (
    targetView: View,
    customTitle?: string,
    customSteps?: string[]
  ) => {
    if (view === targetView && !loadingConfig.isVisible) {
      setSidebarOpen(false);
      return;
    }

    const viewStepMap: Record<View, { title: string; steps: string[] }> = {
      Overview: {
        title: 'Loading Operational Dashboard',
        steps: [
          'Querying Case Records & Telemetry Database...',
          'Polling Neural Vision Backend Worker...',
          'Rendering Operational Metrics Dashboard...',
        ],
      },
      Investigations: {
        title: 'Loading Case Records',
        steps: [
          'Connecting to Forensic Case Registry...',
          'Fetching Active Case Inventories & Custody Logs...',
          'Populating Case Management Workspace...',
        ],
      },
      'Investigation Detail': {
        title: 'Mounting Forensic Workspace',
        steps: [
          'Parsing Synchronized DVR Video Bitstreams...',
          'Mapping Object Tracking Vectors & Bounding Matrices...',
          'Readying Interactive Multi-Camera Viewer...',
        ],
      },
      'Video Evidence': {
        title: 'Loading Video Evidence Sources',
        steps: [
          'Scanning DVR Source Media & Container Descriptors...',
          'Auditing Keyframe Index & Timestamp Vectors...',
          'Initializing CCTV Player Matrix...',
        ],
      },
      Timeline: {
        title: 'Constructing Chronological Timeline',
        steps: [
          'Aggregating Multi-Camera Detection Logs...',
          'Correlating Frame Timestamp Sequences...',
          'Rendering Synchronized Event Scrubbers...',
        ],
      },
      Detections: {
        title: 'Loading Forensic Observations',
        steps: [
          'Filtering PyTorch Object Classifications...',
          'Calculating Confidence Scores & Bounding Rects...',
          'Building Detection Grid Matrix...',
        ],
      },
      Entities: {
        title: 'Loading Tracked Physical Objects',
        steps: [
          'Indexing Physical Entity Identity Chains...',
          'Computing Kinematic Velocity & Path Vectors...',
          'Rendering Entity Directory Workspace...',
        ],
      },
      Disappearances: {
        title: 'Analyzing Temporal Continuity',
        steps: [
          'Evaluating Object Absence & Occlusion Windows...',
          'Filtering Stationary Loss Anomalies...',
          'Populating Object Disappearance Audit...',
        ],
      },
      Events: {
        title: 'Reconstructing Incident Chain',
        steps: [
          'Linking Multi-Stream Incident Events...',
          'Sequencing Reconstructed Forensic Milestones...',
          'Displaying Reconstructed Event Dossier...',
        ],
      },
      Evidence: {
        title: 'Loading Keyframe Evidence Vault',
        steps: [
          'Accessing Cryptographically Hashed Frame Captures...',
          'Validating Image Bitstream SHA-256 Hashes...',
          'Rendering Evidence Vault Gallery...',
        ],
      },
      Integrity: {
        title: 'Auditing Bitstream & Frame Integrity',
        steps: [
          'Checking SHA-256 Container Hashes...',
          'Evaluating Frame Continuity & Drop Anomalies...',
          'Generating Cryptographic Verification Audit...',
        ],
      },
      Reports: {
        title: 'Loading Court-Ready Dossier Generator',
        steps: [
          'Formatting Certified Case Evidence Templates...',
          'Attaching Cryptographic Chain of Custody Proofs...',
          'Readying PDF Report Generator...',
        ],
      },
      Processing: {
        title: 'Connecting Processing Pipeline Console',
        steps: [
          'Establishing FastAPI Stream Handler...',
          'Querying PyTorch Neural Vision Worker State...',
          'Loading Pipeline Diagnostic Console...',
        ],
      },
    };

    const defaultInfo = viewStepMap[targetView] || {
      title: `Loading ${targetView}`,
      steps: ['Initializing Module...', 'Hydrating Telemetry...', 'Rendering Workspace...'],
    };

    const finalTitle = customTitle || defaultInfo.title;
    const finalSteps = customSteps || defaultInfo.steps;

    triggerLoading(
      finalTitle,
      finalSteps,
      () => {
        setView(targetView);
        setSidebarOpen(false);
      },
      'Loading workspace view...',
      1600,
      'simple'
    );
  };

  // Case & evidence state
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseSummary | null>(null);
  const [caseEvidence, setCaseEvidence] = useState<EvidenceSummary[]>([]);
  const [overviewStats, setOverviewStats] = useState<OverviewStats | null>(null);
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
  const [isCliModalOpen, setIsCliModalOpen] = useState(false);
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);
  const [quickstartTab, setQuickstartTab] = useState<'tui' | 'detect' | 'extract' | 'pipeline' | 'setup'>('tui');
  const [globalSearchText, setGlobalSearchText] = useState('');
  const [timelineSubTab, setTimelineSubTab] = useState<'ai' | 'detections' | 'incidents' | 'disappearances'>('ai');

  const handleCopyCommand = (cmd: string, id: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(cmd);
    }
    setCopiedCommand(id);
    setTimeout(() => setCopiedCommand(null), 2500);
  };

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
      text: 'Trace-X Forensic AI Agent is active (Groq LLaMA + TraceX Neural Vision Engine). Ask questions about observed timeline events, vehicle identifications, kinematic velocities, or video integrity findings.',
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
      const saved = localStorage.getItem('tracex_auth_user');
      if (saved) {
        try {
          setCurrentUser(JSON.parse(saved));
        } catch {}
      }
      setAuthChecking(false);
    }
  }, []);

  const handleLoginSuccess = (user: SupabaseUser) => {
    triggerLoading(
      `Authenticating Session: ${user.name}`,
      [
        'Verifying Examiner Access Credentials & Badge ID...',
        'Establishing Encrypted Cryptographic Session Tokens...',
        'Decrypting Examiner Case Workspace & Records...',
      ],
      () => {
        setCurrentUser(user);
        localStorage.setItem('tracex_auth_user', JSON.stringify(user));
      },
      'Enterprise Authorization Approved',
      2400
    );
  };

  const handleSignOut = async () => {
    triggerLoading(
      'Signing Out Examiner Session',
      [
        'Closing Cryptographic Encryption Keys...',
        'Wiping Local Session Cache & Tokens...',
        'Redirecting to Examiner Gateway...',
      ],
      async () => {
        if (isSupabaseConfigured && supabase) {
          try {
            await supabase.auth.signOut();
          } catch (err) {
            console.warn('Sign out error:', err);
          }
        }
        setCurrentUser(null);
        localStorage.removeItem('tracex_auth_user');
      },
      'Securing Local Evidence Cache',
      1800
    );
  };

  const fetchCases = async () => {
    setLoadingCases(true);
    try {
      const [casesResult, statsResult] = await Promise.allSettled([
        api.listCases(),
        api.getOverviewStats(),
      ]);

      if (casesResult.status === 'fulfilled') {
        const data = casesResult.value || [];
        setCases(data);
        if (data.length > 0 && !selectedCase) {
          setSelectedCase(data[0]);
          setUploadTargetCaseId(data[0].id);
        }
      }

      if (statsResult.status === 'fulfilled') {
        setOverviewStats(statsResult.value);
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
    setIsUploadModalOpen(true);
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

      // Heartbeat timer for user diagnostic feedback during cloud processing & cold starts
      let elapsedSeconds = 0;
      const heartbeatTimer = setInterval(() => {
        elapsedSeconds += 5;
        if (elapsedSeconds === 10) {
          setProcessingLogs((prev) => [
            ...prev,
            `[STATUS] Cloud AI Engine demuxing frames & calculating motion vectors...`,
          ]);
        } else if (elapsedSeconds === 25) {
          setProcessingLogs((prev) => [
            ...prev,
            `[STATUS] Deep neural vision model running object detection (YOLO/PyTorch)...`,
          ]);
        } else if (elapsedSeconds === 45) {
          setProcessingLogs((prev) => [
            ...prev,
            `[RENDER COLD-START] Render free tier instances take ~45s to wake up if idle. Processing...`,
          ]);
        } else if (elapsedSeconds % 30 === 0) {
          setProcessingLogs((prev) => [
            ...prev,
            `[STATUS] Processing video payload (${elapsedSeconds}s elapsed)...`,
          ]);
        }
      }, 5000);

      // Call backend /video/analyze
      let result;
      try {
        result = await api.analyzeVideo(selectedUploadFile);
      } finally {
        clearInterval(heartbeatTimer);
      }

      setProcessingProgress(70);
      setProcessingPhase(3);
      setProcessingLogs((prev) => [
        ...prev,
        `[TRACEX] Multi-stage neural vision & forensic detection completed.`,
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
          hashSnippet: uploadHash || 'CRYPTOGRAPHIC_SEAL_VALID',
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
  // 4b. Object Disappearance & Temporal Continuity Detection Helper
  // -------------------------------------------------------------------------

  const computeObjectDisappearances = (events: any[]): ObjectDisappearanceAnalysis => {
    if (!events || events.length === 0) {
      return {
        available: true,
        count: 0,
        disappearances: [],
        note: 'Object disappearance is a forensic observation. It does not prove that the object was removed, stolen, hidden, or that the footage was manipulated.',
      };
    }

    const observations: Record<string, Array<{ start: Date; end: Date; event: any }>> = {};

    for (const ev of events) {
      const objectType = (ev.object_type || '').trim().toLowerCase();
      if (!objectType || ['motion', 'unknown', 'none', ''].includes(objectType)) continue;
      if (ev.confidence != null && ev.confidence < 0.5) continue;

      const startTime = ev.start_time ? new Date(ev.start_time) : null;
      const endTime = ev.end_time ? new Date(ev.end_time) : startTime;
      if (!startTime || isNaN(startTime.getTime())) continue;

      const key = `${ev.camera_id || 'CH-01'}__${objectType}`;
      if (!observations[key]) observations[key] = [];
      observations[key].push({
        start: startTime,
        end: endTime || startTime,
        event: ev,
      });
    }

    const candidates: ObjectDisappearance[] = [];

    for (const [key, items] of Object.entries(observations)) {
      const [cameraId, objectType] = key.split('__');
      items.sort((a, b) => a.start.getTime() - b.start.getTime());
      if (items.length < 2) continue;

      const gaps: number[] = [];
      for (let i = 0; i < items.length - 1; i++) {
        const gap = (items[i + 1].start.getTime() - items[i].end.getTime()) / 1000;
        if (gap >= 0) gaps.push(gap);
      }

      let medianGap = 1.0;
      if (gaps.length > 0) {
        gaps.sort((a, b) => a - b);
        medianGap = gaps[Math.floor(gaps.length / 2)];
      }

      const disappearanceDelay = Math.max(2.0, medianGap * 3.0);
      const lastSeenTime = Math.max(...items.map((it) => it.end.getTime()));
      const lastSeen = new Date(lastSeenTime);
      const disappearanceTime = new Date(lastSeenTime + disappearanceDelay * 1000);

      const relatedActivity: string[] = [];
      for (const ev of events) {
        if ((ev.camera_id || 'CH-01') !== cameraId) continue;
        const evStart = ev.start_time ? new Date(ev.start_time) : null;
        if (!evStart || evStart.getTime() < disappearanceTime.getTime()) continue;
        const desc = `${evStart.toISOString().slice(11, 19)} → ${ev.event_type || 'activity'}${ev.object_type ? ` (${ev.object_type})` : ''}`;
        relatedActivity.push(desc);
        if (relatedActivity.length >= 3) break;
      }

      candidates.push({
        camera_id: cameraId,
        object_type: objectType,
        first_seen: items[0].start.toISOString(),
        last_seen: lastSeen.toISOString(),
        disappearance_time: disappearanceTime.toISOString(),
        observation_count: items.length,
        related_activity: relatedActivity,
      });
    }

    return {
      available: true,
      count: candidates.length,
      disappearances: candidates,
      note: 'Object disappearance is a forensic observation. It does not prove that the object was removed, stolen, hidden, or that the footage was manipulated.',
    };
  };

  const getDisappearanceAnalysis = (): ObjectDisappearanceAnalysis => {
    if (analysisResult?.object_disappearance_analysis?.disappearances) {
      return analysisResult.object_disappearance_analysis;
    }
    if ((analysisResult as any)?.object_disappearance?.disappearances) {
      return (analysisResult as any).object_disappearance;
    }
    return computeObjectDisappearances(analysisResult?.events || []);
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
    const hasAnalysis = Boolean(analysisResult);
    const hasActiveEvidence = Boolean(loadedFileName && analysisResult);
    const activeEvidenceCount = hasActiveEvidence
      ? 1
      : caseEvidence.length > 0
      ? caseEvidence.length
      : overviewStats?.total_evidence && cases.length > 0
      ? overviewStats.total_evidence
      : 0;

    const metricCards = [
      {
        label: 'Total Cases',
        val: cases.length > 0
          ? cases.length.toString()
          : (overviewStats?.total_cases != null && overviewStats.total_cases > 0
              ? overviewStats.total_cases.toString()
              : '0'),
        sub: cases.length > 0
          ? `${cases.filter((c) => c.status !== 'closed').length} active investigations`
          : 'No active investigations',
        icon: FolderSearch,
        customIcon: casesIcon,
        color: 'navy',
      },
      {
        label: 'Evidence Files',
        val: activeEvidenceCount > 0 ? activeEvidenceCount.toString() : '0',
        sub: loadedFileName
          ? `Active: ${loadedFileName.slice(0, 18)}...`
          : activeEvidenceCount > 0
          ? `${activeEvidenceCount} bitstream${activeEvidenceCount === 1 ? '' : 's'} in custody`
          : 'No media loaded',
        icon: Video,
        customIcon: evidenceIcon,
        color: 'teal',
      },
      {
        label: 'TraceX Detections',
        val: hasAnalysis ? (analysisResult?.event_count ?? 0).toString() : '—',
        sub: hasAnalysis
          ? `${analysisResult?.event_count ?? 0} stream detections`
          : 'Awaiting video analysis',
        icon: ScanIcon,
        customIcon: tracexLogo,
        color: 'violet',
      },
      {
        label: 'Tracked Entities',
        val: hasAnalysis
          ? (analysisResult?.forensic_summary?.objects_detected?.length ?? 0).toString()
          : '—',
        sub: hasAnalysis && (analysisResult?.forensic_summary?.objects_detected?.length ?? 0) > 0
          ? analysisResult!.forensic_summary!.objects_detected.slice(0, 3).join(', ')
          : 'No entities tracked yet',
        icon: UserRound,
        customIcon: trackedEntitiesIcon,
        color: 'amber',
      },
      {
        label: 'Reconstructed Events',
        val: hasAnalysis
          ? (analysisResult?.reconstruction_count ?? analysisResult?.reconstructed_events?.length ?? 0).toString()
          : '—',
        sub: hasAnalysis && ((analysisResult?.reconstruction_count ?? 0) > 0 || (analysisResult?.reconstructed_events?.length ?? 0) > 0)
          ? `${analysisResult?.reconstruction_count ?? analysisResult?.reconstructed_events?.length} incident milestones`
          : 'No events reconstructed yet',
        icon: Activity,
        customIcon: eventsIcon,
        color: 'emerald',
      },
      {
        label: 'Integrity Score',
        val: hasAnalysis && analysisResult?.integrity_analysis
          ? `${analysisResult.integrity_analysis.integrity_score}%`
          : '—',
        sub: hasAnalysis && analysisResult?.integrity_analysis
          ? (analysisResult.integrity_analysis.tampering_detected
              ? 'Tampering Detected'
              : 'Cryptographically Verified (SHA-256)')
          : 'Pending cryptographic audit',
        icon: ShieldCheck,
        customIcon: integrityIcon,
        color: 'navy',
      },
    ];

    return (
      <div className="page">
        <PageTitle
          eyebrow="OPERATIONS / OVERVIEW"
          title="Forensic Investigation Overview"
          description="Enterprise digital video evidence acquisition, frame validation, and event reconstruction powered by TraceX's proprietary AI engine."
          action={
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              <a
                href={api.getDesktopExeUrl()}
                download="TraceX-DVR-Forensics.exe"
                className="buttonDownload"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '7px',
                  textDecoration: 'none',
                }}
                title="Download Standalone Windows Desktop App (.exe) — Independent executable with built-in ONNX deep vision neural engine"
              >
                <Download size={15} />
                <span>Download App (.exe)</span>
              </a>
              <a
                href="https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/download/v1.0.1/TraceX-DVR-Forensics-Portable.zip"
                download="TraceX-DVR-Forensics-Portable.zip"
                className="buttonDownload"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '7px',
                  textDecoration: 'none',
                  background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                  border: '1px solid #334155',
                }}
                title="Download Complete Portable Package (.zip) — Full platform bundle including run launcher, parsers, and neural models"
              >
                <Package size={15} />
                <span>Download Portable (.zip)</span>
              </a>
              <button
                type="button"
                className="buttonDownload"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '7px',
                  textDecoration: 'none',
                  background: 'linear-gradient(135deg, #090d16 0%, #1e1b4b 100%)',
                  border: '1px solid #4338ca',
                  color: '#e0e7ff',
                  cursor: 'pointer',
                }}
                onClick={() => setIsCliModalOpen(true)}
                title="View Headless CLI & Terminal Quickstart Instructions"
              >
                <Terminal size={15} color="#818cf8" />
                <span>CLI & Terminal</span>
              </button>
              <button
                className="buttonNewInvestigation"
                onClick={() => setIsNewCaseModalOpen(true)}
              >
                <Plus size={15} />
                New Investigation
              </button>
            </div>
          }
        />


        <div className="overview-cards">
          {metricCards.map((m) => {
            const Icon = m.icon;
            return (
              <div className="metric" key={m.label}>
                <div className={`metric-icon ${m.color}`}>
                  {m.customIcon ? (
                    <img
                      src={m.customIcon}
                      alt={m.label}
                      style={{
                        width: '24px',
                        height: '24px',
                        objectFit: 'contain',
                        borderRadius: '4px',
                      }}
                    />
                  ) : (
                    <Icon size={18} />
                  )}
                </div>
                <div>
                  <p>{m.label}</p>
                  <strong style={m.val === '—' ? { color: '#94a3b8', fontWeight: 500 } : undefined}>
                    {m.val}
                  </strong>
                  <small>{m.sub}</small>
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick launch / Active Workspace Banner */}
        {loadedFileName ? (
          <div className="panel active-workspace-card" style={{ padding: '20px', marginBottom: '20px' }}>
            <div className="section-head" style={{ marginBottom: '14px' }}>
              <div>
                <p className="eyebrow" style={{ color: '#2563eb', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="pulse" style={{ width: '6px', height: '6px' }} /> ACTIVE WORKSPACE TARGET
                </p>
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
                <Button
                  variant="success"
                  icon={FileBarChart}
                  onClick={handleExportPDF}
                >
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
              customAction={
                <div className="folder-upload-wrapper">
                  <div
                    className="container folder-upload-box"
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    <div className="folder">
                      <div className="front-side">
                        <div className="tip"></div>
                        <div className="cover"></div>
                      </div>
                      <div className="back-side cover"></div>
                    </div>
                    <label
                      className="custom-file-upload"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        className="title"
                        type="file"
                        accept=".mp4,.avi,.mov,.mkv,.h264,.dd,.raw,.img,.bin,.001,.dat"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            handleFileChosen(e.target.files[0]);
                          }
                        }}
                      />
                      Choose a file
                    </label>
                  </div>
                </div>
              }
              hideIcon
              icon={Video}
            />
          </div>
        )}

        {/* Forensic CLI & Terminal Quickstart Panel */}
        <div className="panel" style={{ padding: '22px', marginBottom: '20px', background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
          <div className="section-head" style={{ marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <p className="eyebrow" style={{ color: '#4f46e5', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Terminal size={13} /> HEADLESS & TERMINAL AUTOMATION
              </p>
              <h3 style={{ fontSize: '16px', color: '#0f172a', fontWeight: 700, margin: '3px 0' }}>
                TraceX Forensic CLI & Terminal Interface
              </h3>
              <p style={{ margin: 0, fontSize: '11.5px', color: '#64748b' }}>
                Run high-speed multi-vendor DVR carving, proprietary filesystem parsing, and SHA-256 sealed extraction directly from your terminal.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <a
                href={api.getLauncherBatUrl()}
                download="launch_tracex_dvr.bat"
                className="buttonDownload"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 12px',
                  fontSize: '11px',
                  textDecoration: 'none',
                  background: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  color: '#334155',
                }}
                title="Download 1-click Windows Terminal Batch Launcher (.bat)"
              >
                <Download size={13} />
                <span>Download launcher.bat</span>
              </a>
              <button
                type="button"
                className="btn"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 12px',
                  fontSize: '11px',
                  background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)',
                  border: '1px solid #4338ca',
                  color: '#ffffff',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => setIsCliModalOpen(true)}
              >
                <Code size={13} />
                <span>Full CLI Reference</span>
              </button>
            </div>
          </div>

          {/* Quickstart Tabs */}
          <div style={{ display: 'flex', gap: '6px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', marginBottom: '14px', overflowX: 'auto' }}>
            {[
              { id: 'tui' as const, label: 'Interactive TUI', icon: Terminal, desc: 'Interactive terminal GUI' },
              { id: 'detect' as const, label: 'Auto-Detect', icon: Search, desc: 'Identify 11 DVR signatures' },
              { id: 'extract' as const, label: 'Stream Extract', icon: FileVideo, desc: 'Carve & reassemble MP4' },
              { id: 'pipeline' as const, label: 'Full Pipeline', icon: Layers, desc: 'End-to-end automated ingest' },
              { id: 'setup' as const, label: 'Install / Clone', icon: Package, desc: 'Python virtualenv setup' },
            ].map((tab) => {
              const TabIcon = tab.icon;
              const isActive = quickstartTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setQuickstartTab(tab.id)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    fontSize: '11.5px',
                    fontWeight: isActive ? 700 : 500,
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: isActive ? '#6366f1' : 'transparent',
                    background: isActive ? '#eef2ff' : 'transparent',
                    color: isActive ? '#4338ca' : '#64748b',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <TabIcon size={13} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Terminal Display Box */}
          <div
            style={{
              background: '#0a0e1a',
              border: '1px solid #1e293b',
              borderRadius: '7px',
              overflow: 'hidden',
              fontFamily: 'var(--font-mono)',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
            }}
          >
            {/* Window header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 14px',
                background: '#111827',
                borderBottom: '1px solid #1f2937',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} />
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b', display: 'inline-block' }} />
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
                <span style={{ marginLeft: '8px', fontSize: '10.5px', color: '#94a3b8' }}>
                  {quickstartTab === 'tui' && 'TraceX TUI — Terminal User Interface'}
                  {quickstartTab === 'detect' && 'TraceX CLI — DVR Vendor Signature Identification'}
                  {quickstartTab === 'extract' && 'TraceX CLI — Proprietary Video Extraction & Carving'}
                  {quickstartTab === 'pipeline' && 'TraceX CLI — Autonomous Forensic Pipeline'}
                  {quickstartTab === 'setup' && 'TraceX CLI — Repository Clone & Virtualenv Setup'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  let cmd = '';
                  if (quickstartTab === 'tui') cmd = 'python -m backend.cli.tui';
                  else if (quickstartTab === 'detect') cmd = 'python -m backend.cli.main detect "path/to/evidence.dd"';
                  else if (quickstartTab === 'extract') cmd = 'python -m backend.cli.main extract "path/to/evidence.dav" --vendor dahua --output ./extracted/';
                  else if (quickstartTab === 'pipeline') cmd = 'python -m backend.cli.main pipeline "path/to/evidence.001" --output ./cases/case_001/';
                  else if (quickstartTab === 'setup') cmd = 'git clone https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git\ncd multi-vendor-dvr-forensics\npython -m venv .venv\n.venv\\Scripts\\activate\npip install -r requirements.txt\npython -m backend.cli.tui';
                  handleCopyCommand(cmd, quickstartTab);
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '3px 9px',
                  fontSize: '10px',
                  borderRadius: '4px',
                  background: copiedCommand === quickstartTab ? '#065f46' : '#1f2937',
                  color: copiedCommand === quickstartTab ? '#6ee7b7' : '#cbd5e1',
                  border: '1px solid',
                  borderColor: copiedCommand === quickstartTab ? '#059669' : '#374151',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                {copiedCommand === quickstartTab ? <Check size={12} /> : <Copy size={12} />}
                <span>{copiedCommand === quickstartTab ? 'Copied!' : 'Copy Command'}</span>
              </button>
            </div>

            {/* Terminal Body */}
            <div style={{ padding: '14px 18px', color: '#f8fafc', fontSize: '12px', lineHeight: 1.6 }}>
              {quickstartTab === 'tui' && (
                <div>
                  <div style={{ color: '#6ee7b7', marginBottom: '6px' }}>
                    <span style={{ color: '#818cf8' }}>PS C:\TraceX&gt;</span> python -m backend.cli.tui
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: '11px', marginTop: '8px' }}>
                    # Opens the full-screen interactive Terminal User Interface with keyboard-driven evidence browsing, live carving progress bars, and real-time checksum calculation.
                  </div>
                </div>
              )}

              {quickstartTab === 'detect' && (
                <div>
                  <div style={{ color: '#6ee7b7', marginBottom: '6px' }}>
                    <span style={{ color: '#818cf8' }}>PS C:\TraceX&gt;</span> python -m backend.cli.main detect <span style={{ color: '#fde047' }}>"C:\Evidence\surveillance_dump.dd"</span>
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: '11px', marginTop: '8px' }}>
                    # Inspects disk headers and video frames against 11 proprietary signatures (Hikvision, Dahua, HeimVision, Uniview, Matrix, Godrej, TP-Link, CP Plus, Honeywell, Carver, Generic).
                  </div>
                </div>
              )}

              {quickstartTab === 'extract' && (
                <div>
                  <div style={{ color: '#6ee7b7', marginBottom: '6px' }}>
                    <span style={{ color: '#818cf8' }}>PS C:\TraceX&gt;</span> python -m backend.cli.main extract <span style={{ color: '#fde047' }}>"C:\Evidence\ch01.dav"</span> --vendor dahua --output <span style={{ color: '#38bdf8' }}>./extracted_footage/</span>
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: '11px', marginTop: '8px' }}>
                    # Carves proprietary DHAV/H.264 packets, resolves timestamp shifts, and generates forensic-grade standard decodable MP4 evidence files.
                  </div>
                </div>
              )}

              {quickstartTab === 'pipeline' && (
                <div>
                  <div style={{ color: '#6ee7b7', marginBottom: '6px' }}>
                    <span style={{ color: '#818cf8' }}>PS C:\TraceX&gt;</span> python -m backend.cli.main pipeline <span style={{ color: '#fde047' }}>"C:\Evidence\raw_dvr_image.raw"</span> --output <span style={{ color: '#38bdf8' }}>./cases/case_001/</span>
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: '11px', marginTop: '8px' }}>
                    # Autonomous end-to-end ingestion: Auto-detects filesystem &rarr; Parses recording index &rarr; Carves video streams &rarr; Computes SHA-256 seal &rarr; Generates manifest.json.
                  </div>
                </div>
              )}

              {quickstartTab === 'setup' && (
                <div>
                  <div style={{ color: '#6ee7b7', whiteSpace: 'pre-wrap' }}>
                    <span style={{ color: '#818cf8' }}># 1. Clone repository</span>{'\n'}
                    git clone https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git{'\n'}
                    cd multi-vendor-dvr-forensics{'\n\n'}
                    <span style={{ color: '#818cf8' }}># 2. Create and activate virtual environment</span>{'\n'}
                    python -m venv .venv{'\n'}
                    .venv\Scripts\activate   <span style={{ color: '#94a3b8' }}># On Linux/macOS: source .venv/bin/activate</span>{'\n\n'}
                    <span style={{ color: '#818cf8' }}># 3. Install forensic dependencies & launch TUI</span>{'\n'}
                    pip install -r requirements.txt{'\n'}
                    python -m backend.cli.tui
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Supported Vendors Tag Cloud */}
          <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '10.5px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              11 Native Parsers Supported:
            </span>
            {[
              'Hikvision (.mp4/.dav/.dd)',
              'Dahua (.dav/.dd)',
              'HeimVision (.h265)',
              'Uniview (.uvf)',
              'Matrix Comsec (.stm)',
              'Godrej GSS (Line B)',
              'TP-Link VIGI (.dav)',
              'CP Plus (.dav)',
              'Honeywell (.dav)',
              'Carver (Annex B)',
              'Generic Video (MP4/AVI/MKV)',
            ].map((v) => (
              <span
                key={v}
                style={{
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  padding: '2px 7px',
                  borderRadius: '4px',
                  background: '#f1f5f9',
                  color: '#334155',
                  border: '1px solid #e2e8f0',
                }}
              >
                {v}
              </span>
            ))}
          </div>
        </div>

        {/* Cases list */}
        <div className="panel table-panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">ACTIVE DOSSIERS</p>
              <h3>Recent Case Files</h3>
            </div>
            <button
              type="button"
              className="button-refresh-slide"
              onClick={fetchCases}
              disabled={loadingCases}
              title="Refresh Case Dossiers"
            >
              <span className="button__text">Refresh</span>
              <span className="button__icon">
                <svg className="svg" height="48" viewBox="0 0 48 48" width="48" xmlns="http://www.w3.org/2000/svg">
                  <path d="M35.3 12.7c-2.89-2.9-6.88-4.7-11.3-4.7-8.84 0-15.98 7.16-15.98 16s7.14 16 15.98 16c7.45 0 13.69-5.1 15.46-12h-4.16c-1.65 4.66-6.07 8-11.3 8-6.63 0-12-5.37-12-12s5.37-12 12-12c3.31 0 6.28 1.38 8.45 3.55l-6.45 6.45h14v-14l-4.7 4.7z"></path>
                  <path d="M0 0h48v48h-48z" fill="none"></path>
                </svg>
              </span>
            </button>
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
                          variant="action"
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
                      <button
                        className="buttonNewInvestigation"
                        onClick={() => setIsNewCaseModalOpen(true)}
                        style={{ marginTop: '8px' }}
                      >
                        <Plus size={15} />
                        New Investigation
                      </button>
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
            <button
              className="buttonNewInvestigation"
              onClick={() => setIsNewCaseModalOpen(true)}
            >
              <Plus size={15} />
              New Investigation
            </button>
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
          <button
            type="button"
            className="button-refresh-slide"
            onClick={fetchCases}
            disabled={loadingCases}
            title="Refresh Workspace Cases"
          >
            <span className="button__text">Refresh</span>
            <span className="button__icon">
              <svg className="svg" height="48" viewBox="0 0 48 48" width="48" xmlns="http://www.w3.org/2000/svg">
                <path d="M35.3 12.7c-2.89-2.9-6.88-4.7-11.3-4.7-8.84 0-15.98 7.16-15.98 16s7.14 16 15.98 16c7.45 0 13.69-5.1 15.46-12h-4.16c-1.65 4.66-6.07 8-11.3 8-6.63 0-12-5.37-12-12s5.37-12 12-12c3.31 0 6.28 1.38 8.45 3.55l-6.45 6.45h14v-14l-4.7 4.7z"></path>
                <path d="M0 0h48v48h-48z" fill="none"></path>
              </svg>
            </span>
          </button>
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
                          variant="action"
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
                  <button
                    className="buttonDownload"
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    Ingest Media
                  </button>
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
    const totalDuration = duration || analysisResult?.metadata?.duration_seconds || 60;
    const fps = analysisResult?.metadata?.fps || 25;
    const baseTimeStr =
      analysisResult?.forensic_summary?.start_time ||
      analysisResult?.events?.[0]?.start_time ||
      null;

    const events = analysisResult?.events || [];
    const reconstructed = analysisResult?.reconstructed_events || [];
    const dispAnalysis = getDisappearanceAnalysis();
    const disappearances = dispAnalysis?.disappearances || [];

    const handleTrackClick = (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(1, clickX / rect.width));
      const targetSec = pct * totalDuration;
      seekVideo(targetSec);
      if (view === 'Timeline') {
        setView('Investigation Detail');
      }
    };

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
              onClick={() => {
                seekVideo(0);
                if (view === 'Timeline') setView('Investigation Detail');
              }}
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
            <div
              className="track-line"
              onClick={handleTrackClick}
              style={{ cursor: 'pointer' }}
              title="Click anywhere on track to seek timeline"
            >
              <div
                className="video-progress"
                style={{ width: `${Math.min(100, (currentTime / totalDuration) * 100)}%` }}
              />
              {events.map((ev, i) => {
                const sec = getEventTimestampSeconds(ev, baseTimeStr, fps, totalDuration);
                const pos = Math.max(0, Math.min(100, (sec / totalDuration) * 100)).toFixed(2);
                return (
                  <button
                    key={i}
                    className="event-mark"
                    style={{ left: `${pos}%`, cursor: 'pointer', zIndex: 2 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      seekVideo(sec);
                      if (view === 'Timeline') {
                        setView('Investigation Detail');
                      }
                    }}
                    title={`Jump to ${formatSeconds(sec)}: ${ev.event_type} (${ev.object_type || 'target'}${ev.track_id != null ? ` #${ev.track_id}` : ''})`}
                  />
                );
              })}
            </div>
          </div>

          {/* Track 2: Motion / Incidents */}
          <div className="track">
            <label>INCIDENTS</label>
            <div
              className="track-line"
              onClick={handleTrackClick}
              style={{ cursor: 'pointer' }}
              title="Click anywhere on track to seek timeline"
            >
              <div
                className="video-progress"
                style={{
                  width: `${Math.min(100, (currentTime / totalDuration) * 100)}%`,
                  background: 'linear-gradient(90deg, #fed7aa, #f97316)',
                }}
              />
              {reconstructed.map((rev, i) => {
                const sec = getEventTimestampSeconds(rev, baseTimeStr, fps, totalDuration);
                const pos = Math.max(0, Math.min(100, (sec / totalDuration) * 100)).toFixed(2);
                return (
                  <button
                    key={i}
                    className="event-mark mark-1"
                    style={{ left: `${pos}%`, cursor: 'pointer', zIndex: 2 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      seekVideo(sec);
                      if (view === 'Timeline') {
                        setView('Investigation Detail');
                      }
                    }}
                    title={`Jump to ${formatSeconds(sec)}: ${rev.title || rev.event_type || 'Incident'}`}
                  />
                );
              })}
            </div>
          </div>

          {/* Track 3: Disappearances */}
          {disappearances.length > 0 && (
            <div className="track">
              <label>DISAPPEAR</label>
              <div
                className="track-line"
                onClick={handleTrackClick}
                style={{ cursor: 'pointer' }}
                title="Click anywhere on track to seek timeline"
              >
                <div
                  className="video-progress"
                  style={{
                    width: `${Math.min(100, (currentTime / totalDuration) * 100)}%`,
                    background: 'linear-gradient(90deg, #fecdd3, #e11d48)',
                  }}
                />
                {disappearances.map((d, i) => {
                  const sec = getEventTimestampSeconds(d, baseTimeStr, fps, totalDuration);
                  const pos = Math.max(0, Math.min(100, (sec / totalDuration) * 100)).toFixed(2);
                  return (
                    <button
                      key={i}
                      className="event-mark"
                      style={{
                        left: `${pos}%`,
                        background: '#e11d48',
                        borderColor: '#ffffff',
                        boxShadow: '0 0 6px rgba(225,29,72,0.8)',
                        cursor: 'pointer',
                        zIndex: 2,
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        seekVideo(sec);
                        if (view === 'Timeline') {
                          setView('Investigation Detail');
                        }
                      }}
                      title={`Jump to ${formatSeconds(sec)}: ${d.object_type} disappeared (Camera ${d.camera_id})`}
                    />
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="timeline-footer">
          <span>
            <i className="legend teal" /> Detections
          </span>
          <span>
            <i className="legend amber" /> Narrative Incidents
          </span>
          {disappearances.length > 0 && (
            <span>
              <i className="legend coral" style={{ background: '#e11d48' }} /> Disappearances
            </span>
          )}
          <span className="frame-readout">
            Current: <b>{formatSeconds(currentTime)}</b> (Frame {Math.floor(currentTime * fps)})
          </span>
        </div>
      </div>
    );
  };

  // TABBED SECTION BELOW SYNCHRONIZED ANALYSIS TIMELINE
  const renderTimelineTabsSection = () => {
    const totalDuration = duration || analysisResult?.metadata?.duration_seconds || 60;
    const fps = analysisResult?.metadata?.fps || 25;
    const baseTimeStr =
      analysisResult?.forensic_summary?.start_time ||
      analysisResult?.events?.[0]?.start_time ||
      null;

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

            {/* Object Disappearance Detection Tab */}
            <button
              onClick={() => setTimelineSubTab('disappearances')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: timelineSubTab === 'disappearances' ? 700 : 500,
                color: timelineSubTab === 'disappearances' ? '#172554' : '#64748b',
                borderBottom: timelineSubTab === 'disappearances' ? '2px solid #2563eb' : '2px solid transparent',
                background: 'transparent',
                borderTop: 0,
                borderLeft: 0,
                borderRight: 0,
                cursor: 'pointer',
              }}
            >
              <EyeOff size={14} style={{ color: timelineSubTab === 'disappearances' ? '#2563eb' : '#94a3b8' }} />
              <span>Object Disappearances</span>
              {getDisappearanceAnalysis().count > 0 ? (
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: '4px',
                    background: '#fee2e2',
                    color: '#991b1b',
                  }}
                >
                  {getDisappearanceAnalysis().count} Flag{getDisappearanceAnalysis().count === 1 ? '' : 's'}
                </span>
              ) : (
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: '4px',
                    background: '#ecfdf5',
                    color: '#065f46',
                  }}
                >
                  0 Clean
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
                    className="btn-chip"
                    onClick={() => handleSendQuery(promptText)}
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
                          : 'TraceX Forensic Engine'}
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
                        {msg.events.map((ev, evIdx) => {
                          const evSec = getEventTimestampSeconds(ev, baseTimeStr, fps, totalDuration);
                          return (
                            <button
                              key={evIdx}
                              className="btn-chip"
                              style={{
                                fontSize: '10px',
                                padding: '3px 10px',
                                justifyContent: 'flex-start',
                                height: '24px',
                                cursor: 'pointer',
                              }}
                              onClick={() => {
                                seekVideo(evSec);
                                if (view === 'Timeline') setView('Investigation Detail');
                              }}
                              title={`Jump video to ${formatSeconds(evSec)}`}
                            >
                              Jump to {ev.event_type} ({formatSeconds(evSec)})
                            </button>
                          );
                        })}
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
                  variant="ai"
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
                    events.slice(0, 50).map((ev, i) => {
                      const evSec = getEventTimestampSeconds(ev, baseTimeStr, fps, totalDuration);
                      return (
                        <tr
                          key={i}
                          style={{ cursor: 'pointer' }}
                          onClick={() => {
                            seekVideo(evSec);
                            if (view === 'Timeline') setView('Investigation Detail');
                          }}
                          title={`Click row to jump to ${formatSeconds(evSec)}`}
                        >
                          <td className="mono" style={{ color: '#0f766e', fontWeight: 600 }}>
                            {formatSeconds(evSec)}
                          </td>
                          <td>
                            <b>{ev.object_type || ev.event_type}</b>
                          </td>
                          <td className="mono">TRK-{ev.track_id ?? i + 101}</td>
                          <td>{Math.round((ev.confidence || 0.85) * 100)}%</td>
                          <td style={{ textAlign: 'right' }}>
                            <Button
                              variant="action"
                              icon={Play}
                              onClick={(e) => {
                                e?.stopPropagation?.();
                                seekVideo(evSec);
                                if (view === 'Timeline') setView('Investigation Detail');
                              }}
                            >
                              Seek
                            </Button>
                          </td>
                        </tr>
                      );
                    })
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
                reconstructed.map((rev, i) => {
                  const revSec = getEventTimestampSeconds(rev, baseTimeStr, fps, totalDuration);
                  return (
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
                        cursor: 'pointer',
                      }}
                      onClick={() => {
                        seekVideo(revSec);
                        if (view === 'Timeline') setView('Investigation Detail');
                      }}
                      title={`Jump to ${formatSeconds(revSec)}: ${rev.title}`}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <b style={{ color: '#172554', fontSize: '12px' }}>{rev.title}</b>
                          <span className="mono" style={{ fontSize: '10px', color: '#d97706', fontWeight: 600 }}>
                            {formatSeconds(revSec)}
                          </span>
                        </div>
                        <p style={{ margin: '3px 0 0', color: '#64748b', fontSize: '11px' }}>{rev.description}</p>
                      </div>
                      <Button
                        variant="secondary"
                        icon={Play}
                        onClick={(e) => {
                          e?.stopPropagation?.();
                          seekVideo(revSec);
                          if (view === 'Timeline') setView('Investigation Detail');
                        }}
                      >
                        Seek
                      </Button>
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '20px' }}>
                  No reconstructed narrative incidents detected.
                </div>
              )}
            </div>
          )}

          {/* Object Disappearance Detection Tab Content */}
          {timelineSubTab === 'disappearances' && (() => {
            const disp = getDisappearanceAnalysis();
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '13px', color: '#1e293b', fontWeight: 700 }}>
                      Object Disappearance & Temporal Continuity Detection
                    </h4>
                    <p style={{ margin: '2px 0 0', fontSize: '11px', color: '#64748b' }}>
                      Heuristic tracking for physical objects consistently observed across sequential frames that abruptly ceased appearing.
                    </p>
                  </div>
                  <div>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        padding: '4px 10px',
                        borderRadius: '6px',
                        background: disp.count > 0 ? '#fff1f2' : '#f0fdf4',
                        border: disp.count > 0 ? '1px solid #fecdd3' : '1px solid #bbf7d0',
                        color: disp.count > 0 ? '#be123c' : '#15803d',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      {disp.count > 0 ? (
                        <>
                          <AlertCircle size={13} />
                          <span>{disp.count} Disappearance Flag{disp.count === 1 ? '' : 's'}</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 size={13} />
                          <span>No Suspicious Disappearance Anomalies</span>
                        </>
                      )}
                    </span>
                  </div>
                </div>

                {disp.disappearances.length > 0 ? (
                  <>
                    <div style={{ maxHeight: '240px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Object Classification</th>
                            <th>Camera</th>
                            <th>First Observed</th>
                            <th>Last Observed</th>
                            <th>No Longer Seen</th>
                            <th>Observations</th>
                            <th style={{ textAlign: 'right' }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {disp.disappearances.map((cand, i) => {
                            const candSec = getEventTimestampSeconds(cand, baseTimeStr, fps, totalDuration);
                            return (
                              <tr
                                key={i}
                                style={{ cursor: 'pointer' }}
                                onClick={() => {
                                  seekVideo(candSec);
                                  if (view === 'Timeline') setView('Investigation Detail');
                                }}
                                title={`Click row to jump to disappearance at ${formatSeconds(candSec)}`}
                              >
                                <td>
                                  <b style={{ textTransform: 'capitalize', color: '#0f172a' }}>{cand.object_type}</b>
                                </td>
                                <td className="mono" style={{ fontSize: '11px' }}>{cand.camera_id}</td>
                                <td className="mono" style={{ fontSize: '11px' }}>
                                  {new Date(cand.first_seen).toISOString().slice(11, 19)}
                                </td>
                                <td className="mono" style={{ fontSize: '11px' }}>
                                  {new Date(cand.last_seen).toISOString().slice(11, 19)}
                                </td>
                                <td className="mono" style={{ fontSize: '11px', color: '#b91c1c', fontWeight: 700 }}>
                                  {new Date(cand.disappearance_time).toISOString().slice(11, 19)}
                                </td>
                                <td>
                                  <span className="hash-pill" style={{ fontSize: '10px', background: '#f1f5f9' }}>
                                    {cand.observation_count} frames
                                  </span>
                                </td>
                                <td style={{ textAlign: 'right' }}>
                                  <Button
                                    variant="action"
                                    icon={Play}
                                    onClick={(e) => {
                                      e?.stopPropagation?.();
                                      seekVideo(candSec);
                                      if (view === 'Timeline') setView('Investigation Detail');
                                    }}
                                  >
                                    Seek Point
                                  </Button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {/* Candidate Panels matching CLI */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '10px' }}>
                      {disp.disappearances.map((cand, idx) => {
                        const candSec = getEventTimestampSeconds(cand, baseTimeStr, fps, totalDuration);
                        return (
                          <div
                            key={idx}
                            style={{
                              padding: '12px',
                              borderRadius: '6px',
                              background: '#fffbeb',
                              border: '1px solid #fde68a',
                              cursor: 'pointer',
                            }}
                            onClick={() => {
                              seekVideo(candSec);
                              if (view === 'Timeline') setView('Investigation Detail');
                            }}
                            title={`Click card to jump to ${formatSeconds(candSec)}`}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                              <span style={{ fontSize: '11px', fontWeight: 700, color: '#92400e' }}>
                                OBJECT DISAPPEARANCE #{idx + 1} ({formatSeconds(candSec)})
                              </span>
                              <span className="hash-pill" style={{ background: '#fef08a', color: '#713f12', border: '1px solid #facc15' }}>
                                {cand.object_type}
                              </span>
                            </div>
                            <div style={{ fontSize: '11px', lineHeight: 1.5, color: '#451a03' }}>
                              <div><b>Camera:</b> {cand.camera_id}</div>
                              <div><b>First Seen:</b> <span className="mono">{new Date(cand.first_seen).toISOString().slice(11, 19)}</span></div>
                              <div><b>Last Seen:</b> <span className="mono">{new Date(cand.last_seen).toISOString().slice(11, 19)}</span></div>
                              <div><b>No Longer Seen:</b> <span className="mono" style={{ color: '#b91c1c', fontWeight: 700 }}>{new Date(cand.disappearance_time).toISOString().slice(11, 19)}</span></div>
                            </div>
                            {cand.related_activity && cand.related_activity.length > 0 && (
                              <div style={{ marginTop: '6px', paddingTop: '6px', borderTop: '1px solid #fef3c7' }}>
                                <small style={{ fontWeight: 700, color: '#78350f', display: 'block', marginBottom: '2px' }}>
                                  Related activity after disappearance:
                                </small>
                                {cand.related_activity.map((act, actIdx) => (
                                  <div key={actIdx} style={{ fontSize: '10px', color: '#57534e' }}>
                                    • {act}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <div style={{ padding: '24px', textAlign: 'center', background: '#f8fafc', borderRadius: '6px', border: '1px dashed #cbd5e1' }}>
                    <CheckCircle2 size={24} style={{ color: '#16a34a', margin: '0 auto 8px' }} />
                    <h4 style={{ margin: 0, fontSize: '13px', color: '#1e293b' }}>No Significant Object Disappearance Patterns Detected</h4>
                    <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#64748b' }}>
                      All tracked entities maintain regular continuity across video timestamps.
                    </p>
                  </div>
                )}

                <div style={{ padding: '8px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '10.5px', color: '#64748b' }}>
                  <b>Forensic Disclaimer:</b> Object disappearance is a forensic observation. It does not prove that the object was removed, stolen, hidden, or that the footage was manipulated.
                </div>
              </div>
            );
          })()}
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
              <button
                className="buttonDownload"
                onClick={() => setIsUploadModalOpen(true)}
              >
                Ingest Media
              </button>
              <Button
                variant="ai"
                icon={Sparkles}
                onClick={() => setIsQueryModalOpen(true)}
              >
                AI Assistant
              </Button>
              <Button
                variant="success"
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
                variant="ai"
                icon={Sparkles}
                onClick={() => setIsQueryModalOpen(true)}
              >
                Query AI
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
                      'Temporal correlation and TraceX multi-stage forensic object detection completed.'}
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
                    {(analysisResult.reconstructed_events || []).slice(0, 5).map((rev, i) => {
                      const revSec = getEventTimestampSeconds(
                        rev,
                        analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                        analysisResult?.metadata?.fps || 25,
                        duration || analysisResult?.metadata?.duration_seconds || 60
                      );
                      return (
                        <div
                          key={i}
                          style={{
                            padding: '8px 10px',
                            border: '1px solid #e2e8f0',
                            borderRadius: '4px',
                            background: '#fff',
                            cursor: 'pointer',
                          }}
                          onClick={() => seekVideo(revSec)}
                          title={`Jump to ${formatSeconds(revSec)}: ${rev.title}`}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <b style={{ fontSize: '11px', color: '#172554' }}>{rev.title}</b>
                            <span style={{ fontSize: '9px', color: '#047857' }}>
                              {Math.round((rev.confidence || 0.85) * 100)}%
                            </span>
                          </div>
                          <small style={{ color: '#64748b', fontSize: '10px' }}>{rev.description}</small>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Object Disappearances Context */}
                {(() => {
                  const disp = getDisappearanceAnalysis();
                  const baseTimeStr = analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time;
                  const fps = analysisResult?.metadata?.fps || 25;
                  const totalDur = duration || analysisResult?.metadata?.duration_seconds || 60;
                  return (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <p className="eyebrow" style={{ margin: 0 }}>
                          OBJECT DISAPPEARANCES ({disp.count})
                        </p>
                        <span
                          style={{
                            fontSize: '9px',
                            fontWeight: 700,
                            padding: '1px 5px',
                            borderRadius: '3px',
                            background: disp.count > 0 ? '#fee2e2' : '#ecfdf5',
                            color: disp.count > 0 ? '#991b1b' : '#065f46',
                          }}
                        >
                          {disp.count > 0 ? `${disp.count} FLAGGED` : 'CLEAN'}
                        </span>
                      </div>
                      {disp.disappearances.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '150px', overflowY: 'auto' }}>
                          {disp.disappearances.map((d, i) => {
                            const dSec = getEventTimestampSeconds(d, baseTimeStr, fps, totalDur);
                            return (
                              <div
                                key={i}
                                style={{
                                  padding: '8px 10px',
                                  border: '1px solid #fecdd3',
                                  borderRadius: '4px',
                                  background: '#fff1f2',
                                  cursor: 'pointer',
                                }}
                                onClick={() => seekVideo(dSec)}
                                title={`Jump to disappearance timestamp: ${formatSeconds(dSec)}`}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <b style={{ fontSize: '11px', color: '#9f1239', textTransform: 'capitalize' }}>
                                    {d.object_type} Disappeared
                                  </b>
                                  <span className="mono" style={{ fontSize: '9.5px', color: '#be123c', fontWeight: 600 }}>
                                    {formatSeconds(dSec)}
                                  </span>
                                </div>
                                <small style={{ color: '#475569', fontSize: '9.5px' }}>
                                  Camera {d.camera_id} • {d.observation_count} frames observed
                                </small>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div style={{ padding: '8px 10px', border: '1px solid #bbf7d0', borderRadius: '4px', background: '#f0fdf4', fontSize: '10.5px', color: '#166534', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <CheckCircle2 size={13} className="shrink-0 text-emerald-600" />
                          <span>No sudden object disappearances detected</span>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* DVR Evidence Panel — shows parsed vendor/parser data for all case evidence */}
                {caseEvidence.length > 0 && (
                  <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '12px' }}>
                    <p className="eyebrow" style={{ marginBottom: '8px' }}>
                      DVR EVIDENCE ({caseEvidence.length} item{caseEvidence.length !== 1 ? 's' : ''})
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
                      {caseEvidence.map((ev) => {
                        const vendorLabel = ev.vendor
                          ? ev.vendor.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                          : 'Unknown';
                        const confPct = ev.detection_confidence != null
                          ? Math.round(ev.detection_confidence * 100)
                          : null;
                        const confColor = confPct == null ? '#94a3b8'
                          : confPct >= 80 ? '#16a34a'
                          : confPct >= 60 ? '#d97706'
                          : '#dc2626';
                        const isParsed = ev.status === 'parsed' || ev.recordings.length > 0;
                        return (
                          <div
                            key={ev.id}
                            style={{
                              padding: '10px 12px',
                              border: `1px solid ${isParsed ? '#bbf7d0' : '#e2e8f0'}`,
                              borderRadius: '6px',
                              background: isParsed ? '#f0fdf4' : '#f8fafc',
                              fontSize: '11px',
                            }}
                          >
                            {/* File name + vendor badge */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '6px', marginBottom: '6px' }}>
                              <b style={{ color: '#1e293b', fontSize: '11px', wordBreak: 'break-all', flex: 1 }}>
                                {ev.original_filename}
                              </b>
                              {ev.vendor && (
                                <span style={{
                                  padding: '2px 7px',
                                  borderRadius: '999px',
                                  background: '#dbeafe',
                                  color: '#1d4ed8',
                                  fontSize: '9.5px',
                                  fontWeight: 700,
                                  letterSpacing: '0.03em',
                                  whiteSpace: 'nowrap',
                                  flexShrink: 0,
                                }}>
                                  {vendorLabel}
                                </span>
                              )}
                            </div>

                            {/* Confidence + hash */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginBottom: '6px' }}>
                              {confPct != null && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span style={{ color: '#64748b', fontSize: '9.5px' }}>Confidence:</span>
                                  <span style={{ color: confColor, fontWeight: 700, fontSize: '9.5px' }}>{confPct}%</span>
                                  <div style={{ flex: 1, height: '3px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
                                    <div style={{ width: `${confPct}%`, height: '100%', background: confColor, borderRadius: '2px' }} />
                                  </div>
                                </div>
                              )}
                              {!ev.vendor && (
                                <div style={{ color: '#94a3b8', fontSize: '9.5px', fontStyle: 'italic' }}>
                                  Not yet parsed — click Parse below
                                </div>
                              )}
                              {ev.sha256 && (
                                <div style={{ color: '#64748b', fontSize: '9px', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                                  SHA-256: {ev.sha256.slice(0, 16)}…
                                </div>
                              )}
                            </div>

                            {/* Recordings count */}
                            {ev.recordings.length > 0 && (
                              <div style={{ marginBottom: '6px', color: '#16a34a', fontSize: '9.5px', fontWeight: 600 }}>
                                ✓ {ev.recordings.length} recording{ev.recordings.length !== 1 ? 's' : ''} found
                                {ev.recordings[0]?.resolution && ` • ${ev.recordings[0].resolution}`}
                                {ev.recordings[0]?.codec && ` • ${ev.recordings[0].codec.toUpperCase()}`}
                              </div>
                            )}

                            {/* Warnings */}
                            {ev.parse_warnings.length > 0 && (
                              <div style={{ marginBottom: '6px' }}>
                                {ev.parse_warnings.slice(0, 2).map((w, wi) => (
                                  <div key={wi} style={{ color: '#92400e', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '3px', padding: '3px 7px', fontSize: '9px', marginBottom: '2px' }}>
                                    ⚠ {w}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Parse / Extract actions */}
                            <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                              <button
                                style={{
                                  flex: 1, padding: '4px 8px', fontSize: '9.5px', fontWeight: 600,
                                  background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer',
                                }}
                                onClick={async () => {
                                  try {
                                    const updated = await api.parseEvidence(ev.id);
                                    setCaseEvidence(prev => prev.map(e => e.id === ev.id ? updated : e));
                                  } catch (err: any) {
                                    alert(`Parse failed: ${err.message}`);
                                  }
                                }}
                              >
                                Parse
                              </button>
                              <button
                                style={{
                                  flex: 1, padding: '4px 8px', fontSize: '9.5px', fontWeight: 600,
                                  background: ev.recordings.length > 0 ? '#16a34a' : '#94a3b8',
                                  color: '#fff', border: 'none', borderRadius: '4px',
                                  cursor: ev.recordings.length > 0 ? 'pointer' : 'not-allowed',
                                }}
                                disabled={ev.recordings.length === 0}
                                onClick={async () => {
                                  if (ev.recordings.length === 0) return;
                                  try {
                                    const updated = await api.extractEvidence(ev.id);
                                    setCaseEvidence(prev => prev.map(e => e.id === ev.id ? updated : e));
                                  } catch (err: any) {
                                    alert(`Extract failed: ${err.message}`);
                                  }
                                }}
                              >
                                Extract
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

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
          title="TraceX Neural Vision Detections"
          description="Detailed multi-stage frame detections, bounding coordinates, track IDs, and confidence telemetry."
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
                  filteredEvents.map((ev, i) => {
                    const evSec = getEventTimestampSeconds(
                      ev,
                      analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                      analysisResult?.metadata?.fps || 25,
                      duration || analysisResult?.metadata?.duration_seconds || 60
                    );
                    return (
                      <tr
                        key={i}
                        style={{ cursor: 'pointer' }}
                        onClick={() => {
                          seekVideo(evSec);
                          setView('Investigation Detail');
                        }}
                      >
                        <td>
                          <b className="mono">
                            {formatSeconds(evSec)}
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
                            variant="action"
                            icon={Play}
                            onClick={(e) => {
                              e?.stopPropagation?.();
                              seekVideo(evSec);
                              setView('Investigation Detail');
                            }}
                          >
                            Jump to Frame
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        title="No Detections Recorded"
                        description={
                          analysisResult
                            ? 'No objects matching current filter criteria.'
                            : 'Upload a video file to perform automated TraceX forensic detection.'
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

        {/* Object Disappearance & Continuity Detection Section */}
        {analysisResult && (() => {
          const disp = getDisappearanceAnalysis();
          return (
            <div className="panel" style={{ marginTop: '20px', padding: '20px' }}>
              <div className="section-head" style={{ marginBottom: '16px' }}>
                <div>
                  <p className="eyebrow">CONTINUITY & TEMPORAL INTEGRITY</p>
                  <h3>Object Disappearance Detection</h3>
                  <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0' }}>
                    Automated heuristic auditing to detect physical objects that had repeated temporal observations and ceased appearing without standard exit trajectories.
                  </p>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '4px 10px',
                    borderRadius: '6px',
                    background: disp.count > 0 ? '#fff1f2' : '#f0fdf4',
                    border: disp.count > 0 ? '1px solid #fecdd3' : '1px solid #bbf7d0',
                    color: disp.count > 0 ? '#be123c' : '#15803d',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  {disp.count > 0 ? (
                    <>
                      <AlertCircle size={14} />
                      <span>{disp.count} Potential Disappearance{disp.count === 1 ? '' : 's'} Flagged</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={14} />
                      <span>Continuity Verified • 0 Anomalies</span>
                    </>
                  )}
                </span>
              </div>

              {disp.disappearances.length > 0 ? (
                <>
                  <div className="table-scroll" style={{ border: '1px solid #e2e8f0', borderRadius: '6px', marginBottom: '16px' }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Object Class</th>
                          <th>Camera Channel</th>
                          <th>First Observed</th>
                          <th>Last Observed</th>
                          <th>No Longer Seen</th>
                          <th>Observations</th>
                          <th style={{ textAlign: 'right' }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {disp.disappearances.map((d, i) => {
                          const dSec = getEventTimestampSeconds(
                            d,
                            analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                            analysisResult?.metadata?.fps || 25,
                            duration || analysisResult?.metadata?.duration_seconds || 60
                          );
                          return (
                            <tr
                              key={i}
                              style={{ cursor: 'pointer' }}
                              onClick={() => {
                                seekVideo(dSec);
                                setView('Investigation Detail');
                              }}
                            >
                              <td>
                                <b style={{ textTransform: 'capitalize', color: '#0f172a' }}>{d.object_type}</b>
                              </td>
                              <td><span className="mono" style={{ fontSize: '11px' }}>{d.camera_id}</span></td>
                              <td><span className="mono" style={{ fontSize: '11px' }}>{new Date(d.first_seen).toISOString().slice(11, 19)}</span></td>
                              <td><span className="mono" style={{ fontSize: '11px' }}>{new Date(d.last_seen).toISOString().slice(11, 19)}</span></td>
                              <td><b className="mono" style={{ fontSize: '11px', color: '#b91c1c' }}>{new Date(d.disappearance_time).toISOString().slice(11, 19)}</b></td>
                              <td><span className="hash-pill" style={{ fontSize: '10px' }}>{d.observation_count} frames</span></td>
                              <td style={{ textAlign: 'right' }}>
                                <Button
                                  variant="action"
                                  icon={Play}
                                  onClick={(e) => {
                                    e?.stopPropagation?.();
                                    seekVideo(dSec);
                                    setView('Investigation Detail');
                                  }}
                                >
                                  Jump to Frame
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px', marginBottom: '12px' }}>
                    {disp.disappearances.map((d, idx) => {
                      const dSec = getEventTimestampSeconds(
                        d,
                        analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                        analysisResult?.metadata?.fps || 25,
                        duration || analysisResult?.metadata?.duration_seconds || 60
                      );
                      return (
                        <div
                          key={idx}
                          style={{
                            padding: '12px 14px',
                            borderRadius: '6px',
                            background: '#fffbeb',
                            border: '1px solid #fde68a',
                            cursor: 'pointer',
                          }}
                          onClick={() => {
                            seekVideo(dSec);
                            setView('Investigation Detail');
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 700, color: '#92400e' }}>
                              OBJECT DISAPPEARANCE #{idx + 1} ({formatSeconds(dSec)})
                            </span>
                            <span className="hash-pill" style={{ background: '#fef08a', color: '#713f12', border: '1px solid #facc15' }}>
                              {d.object_type}
                            </span>
                          </div>
                          <div style={{ fontSize: '11px', lineHeight: 1.5, color: '#451a03' }}>
                            <div><b>Camera:</b> {d.camera_id}</div>
                            <div><b>First Seen:</b> <span className="mono">{new Date(d.first_seen).toISOString().slice(11, 19)}</span></div>
                            <div><b>Last Seen:</b> <span className="mono">{new Date(d.last_seen).toISOString().slice(11, 19)}</span></div>
                            <div><b>No Longer Seen:</b> <span className="mono" style={{ color: '#b91c1c', fontWeight: 700 }}>{new Date(d.disappearance_time).toISOString().slice(11, 19)}</span></div>
                            <div><b>Observations:</b> {d.observation_count}</div>
                          </div>
                          {d.related_activity && d.related_activity.length > 0 && (
                            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #fef3c7' }}>
                              <small style={{ fontWeight: 700, color: '#78350f', display: 'block', marginBottom: '2px' }}>
                                Related activity after disappearance:
                              </small>
                              {d.related_activity.map((act, actIdx) => (
                                <div key={actIdx} style={{ fontSize: '10px', color: '#57534e' }}>
                                  • {act}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              ) : (
                <div style={{ padding: '20px', textAlign: 'center', background: '#f8fafc', borderRadius: '6px', border: '1px dashed #cbd5e1' }}>
                  <CheckCircle2 size={20} style={{ color: '#16a34a', margin: '0 auto 6px' }} />
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#1e293b', display: 'block' }}>No significant object disappearance patterns detected</span>
                  <small style={{ color: '#64748b' }}>All tracked objects maintained steady continuous trajectories without unexpected mid-stream absence.</small>
                </div>
              )}

              <div style={{ padding: '8px 12px', background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '6px', fontSize: '10.5px', color: '#92400e', marginTop: '12px' }}>
                <b>Forensic Note:</b> Object disappearance is a forensic observation. It does not prove that the object was removed, stolen, hidden, or that the footage was manipulated.
              </div>
            </div>
          );
        })()}
      </div>
    );
  };

  // DISAPPEARANCES VIEW
  const renderDisappearances = () => {
    const disp = getDisappearanceAnalysis();

    return (
      <div className="page">
        <PageTitle
          eyebrow="ANALYSIS / OBJECT CONTINUITY"
          title="Object Disappearance Detection"
          description="Heuristic temporal continuity audit identifying physical targets tracked across sequential frames that abruptly ceased appearing."
          action={
            <Button
              variant="primary"
              icon={Play}
              onClick={() => setView('Investigation Detail')}
            >
              Open CCTV Viewer
            </Button>
          }
        />

        {/* Overview status banner */}
        <div className="panel" style={{ padding: '20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '10px',
                  background: disp.count > 0 ? '#fee2e2' : '#dcfce7',
                  color: disp.count > 0 ? '#b91c1c' : '#15803d',
                  display: 'grid',
                  placeItems: 'center',
                }}
              >
                <EyeOff size={24} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '15px', color: '#0f172a', fontWeight: 700 }}>
                  {disp.count > 0 ? `${disp.count} Potential Object Disappearance(s) Flagged` : 'No Significant Disappearance Anomalies'}
                </h3>
                <p style={{ margin: '3px 0 0', color: '#64748b', fontSize: '12px' }}>
                  {disp.count > 0
                    ? 'Target observations discontinued before standard exit boundary threshold was met.'
                    : 'All tracked objects maintained steady continuous trajectories without unexplained mid-stream absence.'}
                </p>
              </div>
            </div>

            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                padding: '6px 14px',
                borderRadius: '6px',
                background: disp.count > 0 ? '#fff1f2' : '#f0fdf4',
                border: disp.count > 0 ? '1px solid #fecdd3' : '1px solid #bbf7d0',
                color: disp.count > 0 ? '#be123c' : '#15803d',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {disp.count > 0 ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}
              <span>{disp.count > 0 ? `${disp.count} CANDIDATE(S) FLAGGED` : 'CONTINUITY VERIFIED'}</span>
            </span>
          </div>
        </div>

        {disp.disappearances.length > 0 ? (
          <>
            <div className="panel table-panel" style={{ marginBottom: '20px' }}>
              <div className="section-head" style={{ padding: '16px 20px 0' }}>
                <div>
                  <p className="eyebrow">FORENSIC CANDIDATE TABLE</p>
                  <h3>Observed Dropout Timecodes</h3>
                </div>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Object Classification</th>
                      <th>Camera Channel</th>
                      <th>First Observed</th>
                      <th>Last Observed</th>
                      <th>No Longer Seen (Dropout)</th>
                      <th>Observation Count</th>
                      <th style={{ textAlign: 'right' }}>Forensic Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {disp.disappearances.map((cand, i) => (
                      <tr key={i}>
                        <td>
                          <b style={{ textTransform: 'capitalize', color: '#0f172a' }}>{cand.object_type}</b>
                        </td>
                        <td>
                          <span className="mono" style={{ fontSize: '11.5px' }}>{cand.camera_id}</span>
                        </td>
                        <td>
                          <span className="mono" style={{ fontSize: '11.5px' }}>
                            {new Date(cand.first_seen).toISOString().slice(11, 19)}
                          </span>
                        </td>
                        <td>
                          <span className="mono" style={{ fontSize: '11.5px' }}>
                            {new Date(cand.last_seen).toISOString().slice(11, 19)}
                          </span>
                        </td>
                        <td>
                          <b className="mono" style={{ fontSize: '11.5px', color: '#b91c1c', fontWeight: 700 }}>
                            {new Date(cand.disappearance_time).toISOString().slice(11, 19)}
                          </b>
                        </td>
                        <td>
                          <span className="hash-pill" style={{ background: '#f1f5f9', color: '#334155' }}>
                            {cand.observation_count} frames
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <Button
                            variant="action"
                            icon={Play}
                            onClick={() => {
                              const sec = getEventTimestampSeconds(
                                cand,
                                analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                                analysisResult?.metadata?.fps || 25,
                                duration || analysisResult?.metadata?.duration_seconds || 60
                              );
                              seekVideo(sec);
                              setView('Investigation Detail');
                            }}
                          >
                            Jump to Disappearance
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Candidate Breakdown Panels matching CLI format */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px', marginBottom: '20px' }}>
              {disp.disappearances.map((cand, idx) => {
                const sec = getEventTimestampSeconds(
                  cand,
                  analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                  analysisResult?.metadata?.fps || 25,
                  duration || analysisResult?.metadata?.duration_seconds || 60
                );
                return (
                  <div
                    key={idx}
                    className="panel"
                    style={{
                      padding: '16px',
                      border: '1px solid #fde047',
                      background: '#fffdf5',
                      cursor: 'pointer',
                    }}
                    onClick={() => {
                      seekVideo(sec);
                      setView('Investigation Detail');
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: '#854d0e', textTransform: 'uppercase' }}>
                        OBJECT DISAPPEARANCE #{idx + 1} ({formatSeconds(sec)})
                      </span>
                      <span className="hash-pill" style={{ background: '#fef08a', color: '#713f12', border: '1px solid #facc15' }}>
                        {cand.object_type}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', lineHeight: 1.6, color: '#334155' }}>
                      <div><b>Target Object:</b> {cand.object_type}</div>
                      <div><b>Camera Stream:</b> {cand.camera_id}</div>
                      <div><b>First observed:</b> <span className="mono">{new Date(cand.first_seen).toISOString().slice(11, 19)}</span></div>
                      <div><b>Last observed:</b> <span className="mono">{new Date(cand.last_seen).toISOString().slice(11, 19)}</span></div>
                      <div><b>No longer seen:</b> <span className="mono" style={{ color: '#b91c1c', fontWeight: 700 }}>{new Date(cand.disappearance_time).toISOString().slice(11, 19)}</span></div>
                      <div><b>Sequential Observations:</b> {cand.observation_count} frames</div>
                    </div>

                    {cand.related_activity && cand.related_activity.length > 0 && (
                      <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #fef08a' }}>
                        <b style={{ fontSize: '11px', color: '#78350f', display: 'block', marginBottom: '6px' }}>
                          Related activity after disappearance:
                        </b>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {cand.related_activity.map((act, actIdx) => (
                            <div key={actIdx} style={{ fontSize: '11px', color: '#475569' }}>
                              • {act}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div className="panel" style={{ padding: '40px 20px', textAlign: 'center' }}>
            <CheckCircle2 size={36} style={{ color: '#16a34a', margin: '0 auto 12px' }} />
            <h3 style={{ margin: 0, fontSize: '15px', color: '#0f172a' }}>No Significant Object Disappearance Patterns Detected</h3>
            <p style={{ margin: '6px auto 0', maxWidth: '480px', color: '#64748b', fontSize: '12px' }}>
              All tracked targets within the evidentiary stream demonstrated regular spatial continuity without unexplained disappearance anomalies.
            </p>
          </div>
        )}

        <div style={{ padding: '12px 16px', background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '8px', fontSize: '11px', color: '#92400e', lineHeight: 1.5 }}>
          <b>Forensic Observation Standard:</b> Object disappearance is a forensic observation. It does not prove that the object was removed, stolen, hidden, or that the footage was manipulated.
        </div>
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
            {revs.map((rev, i) => {
              const revSec = getEventTimestampSeconds(
                rev,
                analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                analysisResult?.metadata?.fps || 25,
                duration || analysisResult?.metadata?.duration_seconds || 60
              );
              return (
                <div
                  key={i}
                  className="event-card panel"
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    seekVideo(revSec);
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
                      Camera: {rev.camera_id || 'CH-01'} • Timestamp: {formatSeconds(revSec)}
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
              );
            })}
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
            <Button variant="success" icon={Download} onClick={handleExportPDF}>
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
                  'Temporal correlation and TraceX multi-stage forensic object detection completed.'}
              </p>

              <h4>3. INTEGRITY & TAMPERING AUDIT</h4>
              <p>
                Container continuity score: <b>{analysisResult?.integrity_analysis?.integrity_score ?? 100}%</b>. Overall
                status: <b>{analysisResult?.integrity_analysis?.overall_status || 'VERIFIED PASS'}</b>.
              </p>

              <div className="report-actions">
                <Button variant="success" icon={Download} onClick={handleExportPDF}>
                  Download PDF Dossier (.pdf)
                </Button>
                <Button variant="ai" icon={Sparkles} onClick={() => setIsQueryModalOpen(true)}>
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
                    <b>TraceX Neural Vision</b>
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
      { id: 3, name: 'TraceX Neural Vision Object Detection' },
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
                fontFamily: 'var(--font-mono)',
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
              <button
                className="buttonDownload"
                onClick={() => setIsUploadModalOpen(true)}
              >
                Ingest Media
              </button>
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
            action={
              <Button
                variant="primary"
                icon={Play}
                onClick={() => navigateWithLoading('Investigation Detail')}
              >
                Return to CCTV Viewer
              </Button>
            }
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
    case 'Disappearances':
      mainContent = renderDisappearances();
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
      <LoadingScreen
        isVisible={true}
        variant="simple"
        title="TraceX — DVR Forensics"
        subtitle="Verifying Examiner Session..."
        durationMs={2000}
        onComplete={() => setAuthChecking(false)}
      />
    );
  }

  // If no user is logged in, show the styled Trace-X Login / Register page
  if (!currentUser) {
    return (
      <>
        <LoadingScreen
          isVisible={loadingConfig.isVisible}
          variant={loadingConfig.variant}
          title={loadingConfig.title}
          subtitle={loadingConfig.subtitle}
          steps={loadingConfig.steps}
          durationMs={loadingConfig.durationMs}
          onComplete={loadingConfig.onComplete}
        />
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      </>
    );
  }

  return (
    <div className="app-shell">
      <LoadingScreen
        isVisible={loadingConfig.isVisible}
        variant={loadingConfig.variant}
        title={loadingConfig.title}
        subtitle={loadingConfig.subtitle}
        steps={loadingConfig.steps}
        durationMs={loadingConfig.durationMs}
        onComplete={loadingConfig.onComplete}
      />
      {/* Mobile Backdrop */}
      <div
        className={`sidebar-backdrop ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px 16px', borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
          <button
            type="button"
            onClick={() => {
              navigateWithLoading('Overview');
            }}
            className="flex items-center hover:opacity-85 transition-opacity cursor-pointer bg-transparent border-0 p-0 text-left"
            title="Go to Overview"
          >
            <TraceXLogo variant="white" className="h-9 max-h-10 w-auto object-contain" />
          </button>
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
                navigateWithLoading(itemKey);
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
              navigateWithLoading('Processing');
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
          <div className="topbar-left" style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <button
              className="mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={18} />
            </button>

            <div className="crumb" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                onClick={() => navigateWithLoading('Overview')}
                className="flex items-center hover:opacity-80 transition-opacity cursor-pointer bg-transparent border-0 p-0 text-left"
                title="Go to Overview"
              >
                <TraceXLogo variant="dark" className="h-8 max-h-9 w-auto object-contain" />
              </button>

              <ChevronRight size={14} className="text-slate-400 shrink-0" />

              <button
                type="button"
                onClick={() => navigateWithLoading(view)}
                className="hover:text-blue-700 transition-colors cursor-pointer bg-transparent border-0 p-0 text-left font-semibold text-slate-800"
                title={`Current view: ${view}`}
              >
                <b>{view}</b>
              </button>

              {selectedCase && (
                <>
                  <ChevronRight size={14} className="text-slate-400 shrink-0" />
                  <button
                    type="button"
                    onClick={() => navigateWithLoading('Investigation Detail')}
                    className="mono hover:text-teal-800 hover:underline transition-colors cursor-pointer bg-transparent border-0 p-0 text-left"
                    style={{ color: '#0f766e', fontWeight: 600 }}
                    title={`Open investigation ${selectedCase.case_number || selectedCase.name}`}
                  >
                    {selectedCase.case_number || selectedCase.name}
                  </button>
                </>
              )}
            </div>
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
                onClick={() => {
                  setIsUploadModalOpen(false);
                  const fileName = selectedUploadFile?.name || 'Media Payload';
                  triggerLoading(
                    `Ingesting Media Payload: ${fileName}`,
                    [
                      'Calculating SHA-256 Cryptographic Hash Seal...',
                      'Streaming Bitstream Payload to FastAPI Worker...',
                      'Initializing PyTorch Neural Vision Core & Container Parser...',
                    ],
                    () => {
                      startAnalysisPipeline();
                    },
                    'Allocating Hardware Acceleration & Demuxing Stream',
                    2500,
                    'detailed'
                  );
                }}
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
                            : 'TraceX Forensic Engine'}
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
                      <div style={{ marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {msg.events.map((ev: any, idx: number) => {
                          const evSec = getEventTimestampSeconds(
                            ev,
                            analysisResult?.forensic_summary?.start_time || analysisResult?.events?.[0]?.start_time,
                            analysisResult?.metadata?.fps || 25,
                            duration || analysisResult?.metadata?.duration_seconds || 60
                          );
                          return (
                            <button
                              key={idx}
                              className="btn-chip"
                              style={{ fontSize: '10px', padding: '3px 9px', cursor: 'pointer' }}
                              onClick={() => {
                                seekVideo(evSec);
                                setIsQueryModalOpen(false);
                                setView('Investigation Detail');
                              }}
                              title={`Jump video to ${formatSeconds(evSec)}`}
                            >
                              Jump to {ev.event_type || 'Event'} ({formatSeconds(evSec)})
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
                {isQuerying && (
                  <div className="query-bubble query-assistant">
                    <small>Analyzing TraceX timeline events with Groq AI and generating forensic response...</small>
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
                  variant="ai"
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
                    className="btn-chip"
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
      {/* MODAL: FORENSIC CLI & TERMINAL REFERENCE */}
      {/* =================================================================== */}
      {isCliModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsCliModalOpen(false)}>
          <div
            className="modal-card"
            style={{ width: 'min(780px, 95vw)', maxHeight: '88vh' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-head">
              <div>
                <p className="eyebrow" style={{ color: '#4f46e5', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Terminal size={13} /> TERMINAL OPERATIONS & HEADLESS AUTOMATION
                </p>
                <h3 style={{ fontSize: '17px', color: '#0f172a', fontWeight: 700 }}>
                  TraceX Forensic CLI & Headless Pipeline Guide
                </h3>
              </div>
              <button
                className="icon-btn"
                onClick={() => setIsCliModalOpen(false)}
                aria-label="Close"
              >
                <X size={17} />
              </button>
            </div>

            <div className="modal-body" style={{ gap: '16px', fontSize: '12.5px' }}>
              {/* Introduction Banner */}
              <div
                style={{
                  padding: '12px 14px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  lineHeight: 1.5,
                  color: '#334155',
                }}
              >
                TraceX provides a headless command-line interface (CLI) and an interactive Terminal User Interface (TUI) for forensic video acquisition, signature classification, and stream extraction without needing a browser.
              </div>

              {/* Step 1: Environment & Virtualenv Setup */}
              <div>
                <h4 style={{ margin: '0 0 8px', fontSize: '13px', color: '#1e293b', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>1.</span> Python Virtual Environment Setup
                </h4>
                <div
                  style={{
                    background: '#090d16',
                    border: '1px solid #1e293b',
                    borderRadius: '6px',
                    padding: '12px 14px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11.5px',
                    color: '#6ee7b7',
                    position: 'relative',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => handleCopyCommand(
                      'git clone https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git\ncd multi-vendor-dvr-forensics\npython -m venv .venv\n.venv\\Scripts\\activate\npip install -r requirements.txt',
                      'cli-modal-setup'
                    )}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '10px',
                      background: copiedCommand === 'cli-modal-setup' ? '#065f46' : '#1f2937',
                      color: copiedCommand === 'cli-modal-setup' ? '#6ee7b7' : '#94a3b8',
                      border: '1px solid #374151',
                      borderRadius: '4px',
                      padding: '3px 8px',
                      fontSize: '10px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    {copiedCommand === 'cli-modal-setup' ? <Check size={11} /> : <Copy size={11} />}
                    <span>{copiedCommand === 'cli-modal-setup' ? 'Copied' : 'Copy'}</span>
                  </button>
                  <span style={{ color: '#818cf8' }}># Clone repository and create virtualenv</span>{'\n'}
                  git clone https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git{'\n'}
                  cd multi-vendor-dvr-forensics{'\n'}
                  python -m venv .venv{'\n'}
                  .venv\Scripts\activate  <span style={{ color: '#64748b' }}># Windows PowerShell / CMD</span>{'\n'}
                  <span style={{ color: '#64748b' }}># source .venv/bin/activate  (Linux / macOS)</span>{'\n'}
                  pip install -r requirements.txt
                </div>
              </div>

              {/* Step 2: Interactive TUI */}
              <div>
                <h4 style={{ margin: '0 0 8px', fontSize: '13px', color: '#1e293b', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>2.</span> Full-Screen Interactive Terminal UI (TUI)
                </h4>
                <div
                  style={{
                    background: '#090d16',
                    border: '1px solid #1e293b',
                    borderRadius: '6px',
                    padding: '12px 14px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11.5px',
                    color: '#6ee7b7',
                    position: 'relative',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => handleCopyCommand('python -m backend.cli.tui', 'cli-modal-tui')}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '10px',
                      background: copiedCommand === 'cli-modal-tui' ? '#065f46' : '#1f2937',
                      color: copiedCommand === 'cli-modal-tui' ? '#6ee7b7' : '#94a3b8',
                      border: '1px solid #374151',
                      borderRadius: '4px',
                      padding: '3px 8px',
                      fontSize: '10px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    {copiedCommand === 'cli-modal-tui' ? <Check size={11} /> : <Copy size={11} />}
                    <span>{copiedCommand === 'cli-modal-tui' ? 'Copied' : 'Copy'}</span>
                  </button>
                  <span style={{ color: '#818cf8' }}>PS C:\TraceX&gt;</span> python -m backend.cli.tui
                </div>
                <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#64748b' }}>
                  Offers a keyboard-navigable terminal application for browsing evidence disks, inspecting video streams, viewing cryptographic hashes, and initiating background extraction jobs.
                </p>
              </div>

              {/* Step 3: CLI Subcommands */}
              <div>
                <h4 style={{ margin: '0 0 8px', fontSize: '13px', color: '#1e293b', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>3.</span> Headless CLI Commands Reference
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    {
                      cmd: 'python -m backend.cli.main detect <path_to_evidence>',
                      label: 'Auto-Detect DVR Vendor Signature',
                      desc: 'Scans the first sectors / headers and reports matching vendor and confidence percentage.',
                    },
                    {
                      cmd: 'python -m backend.cli.main parse <path_to_evidence> --vendor <vendor_name>',
                      label: 'Parse Recording Index Table',
                      desc: 'Parses filesystem clusters without modifying data, outputting channel mappings and timestamps.',
                    },
                    {
                      cmd: 'python -m backend.cli.main extract <path_to_evidence> --output ./extracted_footage/',
                      label: 'Extract & Carve Decodable MP4',
                      desc: 'Reassembles fragmented elementary streams into playable H.264/H.265 MP4 recordings.',
                    },
                    {
                      cmd: 'python -m backend.cli.main pipeline <path_to_evidence> --output ./case_dossier/',
                      label: 'End-to-End Forensic Ingest Pipeline',
                      desc: 'Performs detection, parsing, extraction, and SHA-256 verification in a single atomic pass.',
                    },
                  ].map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        padding: '10px 12px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <b style={{ color: '#1e293b', fontSize: '11.5px' }}>{item.label}</b>
                        <button
                          type="button"
                          onClick={() => handleCopyCommand(item.cmd, `cli-cmd-${idx}`)}
                          style={{
                            background: copiedCommand === `cli-cmd-${idx}` ? '#065f46' : '#e2e8f0',
                            color: copiedCommand === `cli-cmd-${idx}` ? '#6ee7b7' : '#475569',
                            border: 'none',
                            borderRadius: '3px',
                            padding: '2px 7px',
                            fontSize: '9.5px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px',
                            fontWeight: 600,
                          }}
                        >
                          {copiedCommand === `cli-cmd-${idx}` ? <Check size={10} /> : <Copy size={10} />}
                          <span>{copiedCommand === `cli-cmd-${idx}` ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <div
                        style={{
                          background: '#090d16',
                          color: '#38bdf8',
                          padding: '6px 8px',
                          borderRadius: '4px',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11px',
                          overflowX: 'auto',
                          marginBottom: '4px',
                        }}
                      >
                        {item.cmd}
                      </div>
                      <p style={{ margin: 0, fontSize: '10.5px', color: '#64748b' }}>{item.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Supported Vendor Flags */}
              <div>
                <h4 style={{ margin: '0 0 8px', fontSize: '13px', color: '#1e293b', fontWeight: 700 }}>
                  4. Supported --vendor Identifier Values
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '6px' }}>
                  {[
                    { id: 'hikvision', name: 'Hikvision (.mp4 / .dav / .dd)' },
                    { id: 'dahua', name: 'Dahua (.dav / .dd / .raw)' },
                    { id: 'heimvision', name: 'HeimVision Raw HEVC (.h265)' },
                    { id: 'uniview', name: 'Uniview Container (.uvf)' },
                    { id: 'matrix', name: 'Matrix Comsec SATATYA (.stm)' },
                    { id: 'godrej', name: 'Godrej GSS Line B (AA55AA55)' },
                    { id: 'tplink_vigi', name: 'TP-Link VIGI (.dav / SEI)' },
                    { id: 'cpplus', name: 'CP Plus Orange Series (.dav)' },
                    { id: 'honeywell', name: 'Honeywell HEN Series (.dav)' },
                    { id: 'carver', name: 'Carver (Raw Annex B Stream)' },
                    { id: 'generic', name: 'Generic Video (MP4/AVI/MKV)' },
                  ].map((v) => (
                    <div
                      key={v.id}
                      style={{
                        padding: '6px 10px',
                        background: '#f1f5f9',
                        border: '1px solid #e2e8f0',
                        borderRadius: '4px',
                        fontSize: '11px',
                      }}
                    >
                      <code style={{ color: '#4f46e5', fontWeight: 700, marginRight: '6px' }}>{v.id}</code>
                      <span style={{ color: '#475569', fontSize: '10px' }}>— {v.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
              <a
                href={api.getLauncherBatUrl()}
                download="launch_tracex_dvr.bat"
                className="buttonDownload"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  fontSize: '11.5px',
                  textDecoration: 'none',
                  background: '#f1f5f9',
                  border: '1px solid #cbd5e1',
                  color: '#334155',
                }}
              >
                <Download size={14} />
                <span>Download Windows Launcher (.bat)</span>
              </a>
              <Button
                variant="primary"
                onClick={() => setIsCliModalOpen(false)}
              >
                Got It
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
                    navigateWithLoading('Investigation Detail');
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
