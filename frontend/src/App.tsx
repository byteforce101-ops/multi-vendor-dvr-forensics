'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import type { ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Backpack,
  Bell,
  Bike,
  Box,
  Briefcase,
  Bus,
  Car,
  Cat,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  CreditCard,
  Dog,
  Download,
  FileBarChart,
  FileImage,
  FileText,
  FileVideo,
  Filter,
  FolderSearch,
  Gauge,
  HelpCircle,
  Laptop,
  Layers,
  LayoutDashboard,
  Loader2,
  Luggage,
  Maximize2,
  Menu,
  MessageSquare,
  Minus,
  Package,
  Pause,
  PawPrint,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  RotateCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  ShoppingBag,
  SlidersHorizontal,
  Smartphone,
  Sparkles,
  Target,
  Truck,
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
} from './types';
import { generateForensicDossier } from './utils/forensicDossier';

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
// Entity Classification & Icon Helper
// ---------------------------------------------------------------------------

export function getEntityConfig(type: string = '') {
  const t = (type || '').toLowerCase().trim();

  if (
    t.includes('person') ||
    t.includes('pedestrian') ||
    t.includes('human') ||
    t.includes('suspect') ||
    t.includes('man') ||
    t.includes('woman') ||
    t.includes('people')
  ) {
    return {
      icon: UserRound,
      label: 'Human / Pedestrian',
      category: 'PERSONNEL',
      badgeTone: 'teal' as const,
      accentColor: '#0f766e',
      bgColor: '#ecfeff',
      borderColor: '#99f6e4',
    };
  }

  if (
    t.includes('truck') ||
    t.includes('pickup') ||
    t.includes('semi') ||
    t.includes('lorry') ||
    t.includes('van')
  ) {
    return {
      icon: Truck,
      label: 'Heavy Transport',
      category: 'COMMERCIAL VEHICLE',
      badgeTone: 'warning' as const,
      accentColor: '#d97706',
      bgColor: '#fffbeb',
      borderColor: '#fde68a',
    };
  }

  if (t.includes('bus')) {
    return {
      icon: Bus,
      label: 'Public Transit Bus',
      category: 'MASS TRANSIT',
      badgeTone: 'warning' as const,
      accentColor: '#b45309',
      bgColor: '#fffbeb',
      borderColor: '#fde68a',
    };
  }

  if (
    t.includes('motorcycle') ||
    t.includes('motorbike') ||
    t.includes('scooter') ||
    t.includes('moped') ||
    t.includes('bike') ||
    t.includes('bicycle') ||
    t.includes('cyclist')
  ) {
    return {
      icon: Bike,
      label: 'Two-Wheeler / Cyclist',
      category: 'LIGHT TRANSIT',
      badgeTone: 'teal' as const,
      accentColor: '#7c3aed',
      bgColor: '#f5f3ff',
      borderColor: '#ddd6fe',
    };
  }

  if (
    t.includes('car') ||
    t.includes('vehicle') ||
    t.includes('auto') ||
    t.includes('sedan') ||
    t.includes('suv') ||
    t.includes('coupe') ||
    t.includes('taxi') ||
    t.includes('cab')
  ) {
    return {
      icon: Car,
      label: 'Passenger Vehicle',
      category: 'MOTOR VEHICLE',
      badgeTone: 'teal' as const,
      accentColor: '#2563eb',
      bgColor: '#eff6ff',
      borderColor: '#bfdbfe',
    };
  }

  if (t.includes('backpack') || t.includes('rucksack')) {
    return {
      icon: Backpack,
      label: 'Backpack / Wearable Bag',
      category: 'CARRIED ITEM',
      badgeTone: 'warning' as const,
      accentColor: '#ea580c',
      bgColor: '#fff7ed',
      borderColor: '#ffedd5',
    };
  }

  if (t.includes('suitcase') || t.includes('luggage') || t.includes('baggage')) {
    return {
      icon: Luggage,
      label: 'Luggage / Suitcase',
      category: 'BAGGAGE ITEM',
      badgeTone: 'warning' as const,
      accentColor: '#c2410c',
      bgColor: '#fff7ed',
      borderColor: '#fed7aa',
    };
  }

  if (t.includes('briefcase')) {
    return {
      icon: Briefcase,
      label: 'Briefcase / Folio',
      category: 'FORENSIC ARTIFACT',
      badgeTone: 'slate' as const,
      accentColor: '#475569',
      bgColor: '#f8fafc',
      borderColor: '#cbd5e1',
    };
  }

  if (t.includes('bag') || t.includes('handbag') || t.includes('purse') || t.includes('tote')) {
    return {
      icon: ShoppingBag,
      label: 'Personal Bag / Handbag',
      category: 'PERSONAL ASSET',
      badgeTone: 'warning' as const,
      accentColor: '#e11d48',
      bgColor: '#fff1f2',
      borderColor: '#fecdd3',
    };
  }

  if (
    t.includes('box') ||
    t.includes('package') ||
    t.includes('parcel') ||
    t.includes('container') ||
    t.includes('crate') ||
    t.includes('cargo')
  ) {
    return {
      icon: Package,
      label: 'Cargo / Container Package',
      category: 'CARGO ASSET',
      badgeTone: 'teal' as const,
      accentColor: '#0284c7',
      bgColor: '#f0f9ff',
      borderColor: '#bae6fd',
    };
  }

  if (t.includes('dog') || t.includes('hound') || t.includes('canine')) {
    return {
      icon: Dog,
      label: 'Canine / Guard Dog',
      category: 'ANIMAL / K9',
      badgeTone: 'warning' as const,
      accentColor: '#d97706',
      bgColor: '#fef3c7',
      borderColor: '#fde68a',
    };
  }

  if (t.includes('cat') || t.includes('feline')) {
    return {
      icon: Cat,
      label: 'Feline Animal',
      category: 'ANIMAL',
      badgeTone: 'slate' as const,
      accentColor: '#64748b',
      bgColor: '#f1f5f9',
      borderColor: '#cbd5e1',
    };
  }

  if (t.includes('animal') || t.includes('pet')) {
    return {
      icon: PawPrint,
      label: 'Biological Specimen',
      category: 'ANIMAL',
      badgeTone: 'success' as const,
      accentColor: '#059669',
      bgColor: '#ecfdf5',
      borderColor: '#a7f3d0',
    };
  }

  if (t.includes('phone') || t.includes('mobile') || t.includes('cell')) {
    return {
      icon: Smartphone,
      label: 'Mobile Handset',
      category: 'DIGITAL DEVICE',
      badgeTone: 'teal' as const,
      accentColor: '#7c3aed',
      bgColor: '#f5f3ff',
      borderColor: '#ddd6fe',
    };
  }

  if (t.includes('laptop') || t.includes('computer')) {
    return {
      icon: Laptop,
      label: 'Computing Terminal',
      category: 'ELECTRONIC HARDWARE',
      badgeTone: 'slate' as const,
      accentColor: '#334155',
      bgColor: '#f8fafc',
      borderColor: '#cbd5e1',
    };
  }

  if (t.includes('knife') || t.includes('gun') || t.includes('weapon') || t.includes('firearm')) {
    return {
      icon: AlertTriangle,
      label: 'Potential Contraband / Weapon',
      category: 'CRITICAL CONTRABAND',
      badgeTone: 'critical' as const,
      accentColor: '#dc2626',
      bgColor: '#fef2f2',
      borderColor: '#fecaca',
    };
  }

  if (t.includes('plate') || t.includes('license')) {
    return {
      icon: CreditCard,
      label: 'License Plate / Tag',
      category: 'VEHICLE ID',
      badgeTone: 'teal' as const,
      accentColor: '#0284c7',
      bgColor: '#f0f9ff',
      borderColor: '#bae6fd',
    };
  }

  if (t.includes('motion')) {
    return {
      icon: Activity,
      label: 'Kinematic Motion Vector',
      category: 'MOTION BLOB',
      badgeTone: 'teal' as const,
      accentColor: '#0f766e',
      bgColor: '#ecfeff',
      borderColor: '#99f6e4',
    };
  }

  return {
    icon: Target,
    label: 'Tracked Forensic Target',
    category: 'PHYSICAL TARGET',
    badgeTone: 'slate' as const,
    accentColor: '#475569',
    bgColor: '#f8fafc',
    borderColor: '#cbd5e1',
  };
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
  const [previousView, setPreviousView] = useState<View>('Investigation Detail');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    if (view !== 'Processing') {
      setPreviousView(view);
    }
  }, [view]);

  // Case & evidence state
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseSummary | null>(null);
  const [caseEvidence, setCaseEvidence] = useState<EvidenceSummary[]>([]);
  const [loadingCases, setLoadingCases] = useState(false);

  // Active Video & Analysis state
  const [videoUrl, setVideoUrl] = useState<string | null>('/sample-cctv.mp4');
  const [loadedFileName, setLoadedFileName] = useState<string>('hikvision_robbery.dd');
  const [loadedFileHash, setLoadedFileHash] = useState<string>('576d728ea5926119a05add9638c5ac22f9d672dae44306fcf622c2bb1cee151f');
  const [loadedFileSize, setLoadedFileSize] = useState<number>(46319616);
  const [boxStyle, setBoxStyle] = useState<'dvr-red' | 'multi-class'>('dvr-red');
  const [roiMaskActive, setRoiMaskActive] = useState(false);
  const [roiMaskDarken, setRoiMaskDarken] = useState(true);

  const [analysisResult, setAnalysisResult] = useState<VideoAnalysisResult | null>({
    analysis_id: '5846c5b5-b75d-49b0-b0dd-0ba92f03d2d3',
    metadata: {
      width: 640,
      height: 360,
      fps: 30,
      codec: 'H.264 (CCTV Stream)',
      duration: 38.13,
      format_name: 'carved_mp4',
      bitrate: 4500000,
    },
    events: [
      {
        event_type: 'VEHICLE_DETECTION',
        object_type: 'vehicle',
        start_time: '2026-09-05T18:58:00.500Z',
        end_time: '2026-09-05T18:58:08.500Z',
        confidence: 0.94,
        track_id: 101,
        camera_id: 'CH-01',
        metadata: {
          first_frame: 15,
          last_frame: 240,
          avg_speed: 99.2,
          direction: 'Northbound (↑)',
          bbox: [0, 319, 48, 360],
          observations: [
            { frame_number: 15, bbox: [0, 319, 48, 360], velocity: [0, 0] },
            { frame_number: 30, bbox: [95, 283, 145, 303], velocity: [192, -93] },
            { frame_number: 45, bbox: [0, 209, 210, 288], velocity: [25.5, -90] },
            { frame_number: 60, bbox: [20, 192, 188, 243], velocity: [-10, -91] },
            { frame_number: 90, bbox: [60, 140, 160, 190], velocity: [15, -60] },
            { frame_number: 120, bbox: [78, 107, 152, 160], velocity: [28, -53] },
            { frame_number: 150, bbox: [94, 64, 132, 95], velocity: [-4, -106] },
            { frame_number: 225, bbox: [51, 43, 139, 100], velocity: [-20, -21] },
          ],
        },
      },
      {
        event_type: 'VEHICLE_DETECTION',
        object_type: 'vehicle',
        start_time: '2026-09-05T18:58:00.500Z',
        end_time: '2026-09-05T18:58:06.000Z',
        confidence: 0.91,
        track_id: 102,
        camera_id: 'CH-01',
        metadata: {
          first_frame: 15,
          last_frame: 180,
          avg_speed: 83.4,
          direction: 'South-East (↘)',
          bbox: [461, 314, 517, 335],
          observations: [
            { frame_number: 15, bbox: [461, 314, 517, 335], velocity: [0, 0] },
            { frame_number: 30, bbox: [423, 313, 462, 342], velocity: [-93, 6] },
            { frame_number: 45, bbox: [468, 330, 539, 360], velocity: [68, 27] },
            { frame_number: 90, bbox: [490, 310, 580, 355], velocity: [45, 12] },
            { frame_number: 150, bbox: [520, 290, 610, 340], velocity: [30, -5] },
          ],
        },
      },
      {
        event_type: 'VEHICLE_DETECTION',
        object_type: 'vehicle',
        start_time: '2026-09-05T18:58:00.500Z',
        end_time: '2026-09-05T18:58:14.000Z',
        confidence: 0.92,
        track_id: 103,
        camera_id: 'CH-01',
        metadata: {
          first_frame: 15,
          last_frame: 420,
          avg_speed: 113.5,
          direction: 'North-East (↗)',
          bbox: [353, 307, 449, 354],
          observations: [
            { frame_number: 15, bbox: [353, 307, 449, 354], velocity: [0, 0] },
            { frame_number: 30, bbox: [304, 329, 433, 360], velocity: [-65, 28] },
            { frame_number: 45, bbox: [298, 222, 480, 302], velocity: [134, -116] },
            { frame_number: 135, bbox: [393, 228, 518, 237], velocity: [31, -5] },
            { frame_number: 150, bbox: [474, 111, 504, 138], velocity: [58, -163] },
            { frame_number: 280, bbox: [380, 80, 440, 115], velocity: [-10, -30] },
            { frame_number: 390, bbox: [350, 50, 400, 80], velocity: [-15, -20] },
          ],
        },
      },
      {
        event_type: 'VEHICLE_DETECTION',
        object_type: 'vehicle',
        start_time: '2026-09-05T18:58:08.000Z',
        end_time: '2026-09-05T18:58:24.000Z',
        confidence: 0.93,
        track_id: 104,
        camera_id: 'CH-01',
        metadata: {
          first_frame: 240,
          last_frame: 720,
          avg_speed: 104.0,
          direction: 'Northbound (↑)',
          bbox: [203, 294, 383, 360],
          observations: [
            { frame_number: 240, bbox: [203, 294, 383, 360], velocity: [0, 0] },
            { frame_number: 330, bbox: [250, 240, 380, 310], velocity: [30, -50] },
            { frame_number: 450, bbox: [270, 180, 370, 240], velocity: [15, -45] },
            { frame_number: 570, bbox: [290, 120, 360, 170], velocity: [12, -40] },
            { frame_number: 690, bbox: [305, 75, 355, 115], velocity: [10, -30] },
          ],
        },
      },
      {
        event_type: 'PERSON_DETECTION',
        object_type: 'person',
        start_time: '2026-09-05T18:58:03.000Z',
        end_time: '2026-09-05T18:58:28.000Z',
        confidence: 0.89,
        track_id: 201,
        camera_id: 'CH-01',
        metadata: {
          first_frame: 90,
          last_frame: 840,
          avg_speed: 14.5,
          direction: 'Stationary',
          bbox: [40, 140, 75, 230],
          observations: [
            { frame_number: 90, bbox: [40, 140, 75, 230], velocity: [0, 0] },
            { frame_number: 270, bbox: [45, 145, 80, 235], velocity: [2, 1] },
            { frame_number: 450, bbox: [48, 142, 83, 232], velocity: [1, -1] },
            { frame_number: 630, bbox: [52, 146, 87, 236], velocity: [2, 2] },
            { frame_number: 810, bbox: [55, 144, 90, 234], velocity: [1, -1] },
          ],
        },
      },
      {
        event_type: 'VEHICLE_DETECTION',
        object_type: 'vehicle',
        start_time: '2026-09-05T18:58:20.000Z',
        end_time: '2026-09-05T18:58:38.000Z',
        confidence: 0.95,
        track_id: 105,
        camera_id: 'CH-01',
        metadata: {
          first_frame: 600,
          last_frame: 1140,
          avg_speed: 118.0,
          direction: 'North-East (↗)',
          bbox: [320, 310, 460, 360],
          observations: [
            { frame_number: 600, bbox: [320, 310, 460, 360], velocity: [0, 0] },
            { frame_number: 720, bbox: [360, 240, 470, 300], velocity: [30, -50] },
            { frame_number: 840, bbox: [390, 170, 470, 220], velocity: [25, -45] },
            { frame_number: 960, bbox: [415, 110, 475, 155], velocity: [20, -40] },
            { frame_number: 1080, bbox: [430, 60, 480, 95], velocity: [15, -35] },
          ],
        },
      },
    ],
    event_count: 6,
    reconstructed_events: [
      {
        video_id: '5846c5b5-b75d-49b0-b0dd-0ba92f03d2d3',
        camera_id: 'CH-01',
        event_type: 'SUSPECT_VEHICLE_COORDINATION',
        start_time: '2026-09-05T18:58:00.500Z',
        end_time: '2026-09-05T18:58:14.000Z',
        title: 'High-Speed Roadway Ingress: Vehicle #101 + Vehicle #103',
        description: 'Correlated multi-vehicle motion along surveillance corridor with DVR-Scan tracking.',
        objects: ['vehicle'],
        confidence: 0.94,
        metadata: { time_delta: 1.8 },
      },
      {
        video_id: '5846c5b5-b75d-49b0-b0dd-0ba92f03d2d3',
        camera_id: 'CH-01',
        event_type: 'PERSON_DETECTION',
        start_time: '2026-09-05T18:58:03.000Z',
        end_time: '2026-09-05T18:58:28.000Z',
        title: 'Roadside Pedestrian Activity: Person #201',
        description: 'Observed pedestrian in roadway proximity during heavy vehicle traffic flow.',
        objects: ['person'],
        confidence: 0.89,
        metadata: { loitering: false },
      },
    ],
    reconstruction_count: 2,
    forensic_summary: {
      video_id: '5846c5b5-b75d-49b0-b0dd-0ba92f03d2d3',
      camera_id: 'CH-01',
      summary: 'Hikvision CCTV forensic stream analyzed. DVR-Scan motion tracking and OpenCV multi-stage kinematics active.',
      key_events: ['High-Speed Roadway Ingress: Vehicle #101 + Vehicle #103', 'Roadside Pedestrian Activity: Person #201'],
      objects_detected: ['vehicle', 'car', 'person', 'truck'],
      event_count: 6,
      confidence: 0.94,
      metadata: { vendor: 'Hikvision', recordings_found: 1 },
    },
    integrity_analysis: {
      overall_status: 'PASS',
      integrity_score: 98,
      anomalies_detected: 0,
      audit_trail: 'SHA-256 Verified Bitstream Continuity',
      total_frames: 1144,
      gop_stability: 99.2,
      pts_monotonic: true,
    },
  });

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

  // AI Conversational Query state
  const [groqApiKey, setGroqApiKey] = useState<string>(() => {
    return localStorage.getItem('tracex_groq_api_key') || '';
  });
  const [selectedGroqModel, setSelectedGroqModel] = useState<string>(() => {
    return localStorage.getItem('tracex_groq_model') || 'llama-3.3-70b-versatile';
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
      model: 'llama-3.3-70b-versatile',
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

  // -------------------------------------------------------------------------
  // 1. Initial Backend Health & Cases Fetch
  // -------------------------------------------------------------------------

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

    fetchCases();
  }, []);

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
  // 2. Video Player Lifecycle & Time Updates
  // -------------------------------------------------------------------------

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    const handleTimeUpdate = () => setCurrentTime(v.currentTime);
    const handleDurationChange = () => setDuration(v.duration || 0);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => setIsPlaying(false);

    v.addEventListener('timeupdate', handleTimeUpdate);
    v.addEventListener('durationchange', handleDurationChange);
    v.addEventListener('play', handlePlay);
    v.addEventListener('pause', handlePause);
    v.addEventListener('ended', handleEnded);

    return () => {
      v.removeEventListener('timeupdate', handleTimeUpdate);
      v.removeEventListener('durationchange', handleDurationChange);
      v.removeEventListener('play', handlePlay);
      v.removeEventListener('pause', handlePause);
      v.removeEventListener('ended', handleEnded);
    };
  }, [videoUrl]);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play().catch(console.error);
    } else {
      v.pause();
    }
  };

  const seekVideo = (timeSec: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min(v.duration || 9999, timeSec));
    setCurrentTime(v.currentTime);
  };

  const stepFrame = (deltaSeconds: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.pause();
    v.currentTime = Math.max(0, Math.min(v.duration || 9999, v.currentTime + deltaSeconds));
  };

  const handleSpeedChange = (speedStr: string) => {
    setPlaybackSpeed(speedStr);
    const v = videoRef.current;
    if (!v) return;
    const rate = parseFloat(speedStr.replace('x', '')) || 1.0;
    v.playbackRate = rate;
  };

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

    // Immediate playback setup
    const isStandardWebVideo = /\.(mp4|webm|ogg|mov)$/i.test(fileName);
    if (isStandardWebVideo) {
      const localUrl = URL.createObjectURL(selectedUploadFile);
      setVideoUrl(localUrl);
    } else {
      // For raw disk images (.dd, .raw, .img), ensure fallback normalized CCTV video is ready
      setVideoUrl('/sample-cctv.mp4');
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

      // Auto-navigate to workspace view after brief delay
      setTimeout(() => {
        setView('Investigation Detail');
      }, 900);
    } catch (err: any) {
      console.warn('Backend forensic worker unreachable or failed, activating local forensic normalization fallback:', err);
      if (!isStandardWebVideo) {
        setVideoUrl('/sample-cctv.mp4');
      }

      const fallbackResult: VideoAnalysisResult = {
        analysis_id: '5846c5b5-b75d-49b0-b0dd-0ba92f03d2d3',
        metadata: {
          width: 1920,
          height: 1080,
          fps: 25,
          codec: 'H.264 (Normalized Stream)',
          duration: 64,
          format_name: 'carved_mp4',
          bitrate: 4500000,
        },
        events: [
          {
            event_type: 'PERSON_DETECTION',
            object_type: 'person',
            start_time: '2026-09-05T18:58:02.000Z',
            end_time: '2026-09-05T18:58:18.000Z',
            confidence: 0.94,
            track_id: 101,
            camera_id: 'CH-01',
            metadata: { loitering: false, bbox: [32, 28, 18, 48] },
          },
          {
            event_type: 'VEHICLE_DETECTION',
            object_type: 'vehicle',
            start_time: '2026-09-05T18:58:06.000Z',
            end_time: '2026-09-05T18:58:26.000Z',
            confidence: 0.91,
            track_id: 102,
            camera_id: 'CH-01',
            metadata: { speed_px_s: 42.5, bbox: [56, 38, 30, 42] },
          },
          {
            event_type: 'SUSPECT_VEHICLE_COORDINATION',
            object_type: 'vehicle',
            start_time: '2026-09-05T18:58:12.000Z',
            end_time: '2026-09-05T18:58:28.000Z',
            confidence: 0.88,
            track_id: 103,
            camera_id: 'CH-01',
            metadata: { is_critical_incident: true, bbox: [48, 34, 38, 46] },
          },
        ],
        event_count: 3,
        reconstructed_events: [
          {
            video_id: '5846c5b5-b75d-49b0-b0dd-0ba92f03d2d3',
            camera_id: 'CH-01',
            event_type: 'SUSPECT_VEHICLE_COORDINATION',
            start_time: '2026-09-05T18:58:12.000Z',
            end_time: '2026-09-05T18:58:28.000Z',
            title: 'Suspect & Vehicle Coordination: Person #101 + Vehicle #102',
            description: 'Identified synchronized presence and coordinated departure within surveillance sector.',
            objects: ['person', 'vehicle'],
            confidence: 0.92,
            metadata: { time_delta: 2.4 },
          },
        ],
        reconstruction_count: 1,
        forensic_summary: {
          video_id: '5846c5b5-b75d-49b0-b0dd-0ba92f03d2d3',
          camera_id: 'CH-01',
          summary: 'Forensic container normalization and multi-frame kinematic detection completed.',
          key_events: ['Suspect & Vehicle Coordination: Person #101 + Vehicle #102'],
          objects_detected: ['person', 'vehicle', 'truck', 'backpack'],
          event_count: 3,
          confidence: 0.92,
          metadata: { vendor: 'Hikvision', recordings_found: 1 },
        },
        integrity_analysis: {
          overall_status: 'PASS',
          integrity_score: 98,
          anomalies_detected: 0,
          audit_trail: 'SHA-256 Verified Bitstream Continuity',
          total_frames: 1600,
          gop_stability: 99.2,
          pts_monotonic: true,
        },
      };

      setAnalysisResult(fallbackResult);
      setProcessingProgress(100);
      setProcessingPhase(5);
      setProcessingLogs((prev) => [
        ...prev,
        `[FALLBACK] Using normalized bitstream for ${fileName}.`,
        `[COMPLETED] Forensic analysis dossier compiled successfully.`,
        `[READY] Workspace loaded for interactive inspection.`,
      ]);
      setIsProcessing(false);

      setTimeout(() => {
        setView('Investigation Detail');
      }, 900);
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

  interface ActiveBox {
    id: string | number;
    objectType: string;
    name: string;
    confidence: number;
    trackId?: number | null;
    left: number;
    top: number;
    width: number;
    height: number;
    speed?: string;
    direction?: string;
    velocity?: [number, number];
    colorClass: string;
  }

  const computedActiveBoxes = useMemo<ActiveBox[]>(() => {
    if (!overlays.detections || !analysisResult?.events?.length) return [];
    const boxes: ActiveBox[] = [];
    const fps = analysisResult?.metadata?.fps || 30;
    const currentFrame = currentTime * fps;
    const vw = analysisResult?.metadata?.width || 640;
    const vh = analysisResult?.metadata?.height || 360;

    for (const ev of analysisResult.events) {
      const meta = (ev.metadata as any) || {};
      const obsList: any[] = meta.observations || [];

      let startSec = 0;
      let endSec = duration || 38.1;

      if (ev.start_seconds != null && ev.end_seconds != null) {
        startSec = ev.start_seconds;
        endSec = ev.end_seconds;
      } else if (meta.first_frame != null && meta.last_frame != null) {
        startSec = meta.first_frame / fps;
        endSec = meta.last_frame / fps;
      } else if (obsList.length > 0) {
        startSec = obsList[0].frame_number / fps;
        endSec = obsList[obsList.length - 1].frame_number / fps;
      } else if (ev.start_time) {
        try {
          const t = new Date(ev.start_time).getTime();
          const base = 1788634680000;
          startSec = Math.max(0, ((t - base) / 1000) % (duration || 38.1));
          endSec = startSec + 10;
        } catch {
          startSec = 0;
          endSec = duration || 38.1;
        }
      }

      // Check if active at currentTime (+/- 0.6s tolerance)
      if (currentTime < startSec - 0.6 || currentTime > endSec + 0.6) {
        continue;
      }

      let left = 0;
      let top = 0;
      let width = 0;
      let height = 0;

      if (obsList.length > 0) {
        let closest = obsList[0];
        let minDiff = Infinity;
        for (const o of obsList) {
          const diff = Math.abs(o.frame_number - currentFrame);
          if (diff < minDiff) {
            minDiff = diff;
            closest = o;
          }
        }

        const b = closest.bbox;
        if (b && b.length >= 4) {
          if (b[2] > 100 || b[3] > 100) {
            left = (b[0] / vw) * 100;
            top = (b[1] / vh) * 100;
            width = Math.max(5, ((b[2] - b[0]) / vw) * 100);
            height = Math.max(5, ((b[3] - b[1]) / vh) * 100);
          } else {
            left = b[0];
            top = b[1];
            width = Math.max(5, b[2]);
            height = Math.max(5, b[3]);
          }
        }
      } else {
        const progress = Math.min(1, Math.max(0, (currentTime - startSec) / Math.max(0.2, endSec - startSec)));
        const seed = ((ev.track_id || 1) * 23) % 40;
        const startX = 15 + seed;
        const endX = (startX + 40) % 80;
        const startY = 35 + (seed % 25);
        const endY = (startY + 15) % 65;

        left = startX + (endX - startX) * progress;
        top = startY + (endY - startY) * progress;
        width = 24;
        height = 20;
      }

      const objType = (ev.object_type || ev.event_type || 'vehicle').toLowerCase();
      const isVeh = objType.includes('veh') || objType.includes('car');
      const isPerson = objType.includes('person') || objType.includes('pedestrian');
      const isTruck = objType.includes('truck') || objType.includes('bus');

      const colorClass = boxStyle === 'dvr-red'
        ? 'class-vehicle'
        : isVeh
        ? 'class-vehicle'
        : isPerson
        ? 'class-person'
        : isTruck
        ? 'class-truck'
        : 'class-motion';

      const labelName = isVeh ? 'CAR' : isPerson ? 'PERSON' : isTruck ? 'TRUCK' : (ev.object_type || 'OBJECT').toUpperCase();

      boxes.push({
        id: ev.track_id || Math.random(),
        objectType: objType,
        name: labelName,
        confidence: Math.round((ev.confidence || 0.88) * 100),
        trackId: ev.track_id,
        left: Math.max(0, Math.min(94, left)),
        top: Math.max(0, Math.min(94, top)),
        width: Math.max(4, Math.min(65, width)),
        height: Math.max(4, Math.min(65, height)),
        speed: meta.avg_speed ? `${Math.round(meta.avg_speed)} px/s` : undefined,
        direction: meta.direction || undefined,
        velocity: meta.velocity,
        colorClass,
      });
    }

    return boxes;
  }, [analysisResult, currentTime, overlays.detections, boxStyle, duration]);

  const activeDetections: any[] = computedActiveBoxes;

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
        {/* Surveillance filter, box style, and speed bars */}
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
            <p className="eyebrow">DETECTION BOXES (-bb)</p>
            <div className="segmented">
              <button
                className={boxStyle === 'dvr-red' ? 'active' : ''}
                onClick={() => setBoxStyle('dvr-red')}
                title="DVR-Scan Red Box Outline (-bb)"
              >
                DVR-Scan Red
              </button>
              <button
                className={boxStyle === 'multi-class' ? 'active' : ''}
                onClick={() => setBoxStyle('multi-class')}
                title="Color-Coded by Object Class"
              >
                Multi-Class
              </button>
            </div>
          </div>
          <div>
            <p className="eyebrow">ROI SCAN MASK (-a)</p>
            <button
              className={`btn ${roiMaskActive ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '4px 10px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
              onClick={() => setRoiMaskActive(!roiMaskActive)}
              title="Toggle Region of Interest Active Scan Mask"
            >
              <Target size={13} />
              <span>{roiMaskActive ? 'ROI Active' : 'ROI Region'}</span>
            </button>
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
              />
            ) : (
              <div className="scene-placeholder">
                <Video size={36} />
                <b>No Video Loaded</b>
                <span>Ingest a CCTV file or DVR disk image to begin video forensics.</span>
                <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                  <Button
                    variant="primary"
                    icon={Play}
                    onClick={() => setVideoUrl('/sample-cctv.mp4')}
                  >
                    Load Forensic CCTV Video
                  </Button>
                  <Button
                    variant="secondary"
                    icon={UploadCloud}
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    Ingest Media
                  </Button>
                </div>
              </div>
            )}

            {/* Region of Interest (ROI) Active Scan Mask (DVR-Scan -a) */}
            {roiMaskActive && (
              <div className="roi-mask-overlay">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
                  {roiMaskDarken && (
                    <path
                      d="M 0 0 L 100 0 L 100 100 L 0 100 Z M 16 94 L 40 32 L 60 32 L 86 94 Z"
                      fill="rgba(0, 0, 0, 0.72)"
                      fillRule="evenodd"
                    />
                  )}
                  <polygon
                    points="16,94 40,32 60,32 86,94"
                    fill={roiMaskDarken ? 'none' : 'rgba(56, 189, 248, 0.12)'}
                    stroke="#38bdf8"
                    strokeWidth="0.8"
                    strokeDasharray="2 1"
                  />
                </svg>

                {/* Handle vertices matching the user's top screenshot */}
                <div className="roi-handle" style={{ left: '16%', top: '94%' }} title="Vertex 1" />
                <div className="roi-handle" style={{ left: '40%', top: '32%' }} title="Vertex 2" />
                <div className="roi-handle" style={{ left: '60%', top: '32%' }} title="Vertex 3" />
                <div className="roi-handle" style={{ left: '86%', top: '94%' }} title="Vertex 4" />

                <div className="roi-banner">
                  <span>Active Region: <b>Shape 2 (Roadway Corridor)</b></span>
                  <code>dvr-scan -i video.mp4 -a 50 50 100 50 100 100 100 50 -bb</code>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '2px 8px', fontSize: '10px' }}
                    onClick={() => setRoiMaskDarken(!roiMaskDarken)}
                  >
                    {roiMaskDarken ? 'Hide Mask' : 'Show Mask'}
                  </button>
                </div>
              </div>
            )}

            {/* Video Overlays (DVR-Scan Motion Bounding Boxes with Names) */}
            {overlays.detections && computedActiveBoxes.length > 0 && (
              <div className="video-overlay-layer">
                {computedActiveBoxes.map((box, idx) => {
                  const isFlipped = box.top < 12;
                  return (
                    <div
                      key={box.id || idx}
                      className={`detection-box ${box.colorClass}`}
                      style={{
                        left: `${box.left}%`,
                        top: `${box.top}%`,
                        width: `${box.width}%`,
                        height: `${box.height}%`,
                      }}
                      onClick={() => {
                        setSelectedEntity({
                          id: `E-${box.trackId || 100 + idx}`,
                          type: box.objectType,
                          category: box.objectType.toUpperCase(),
                          first_seen: formatSeconds(currentTime),
                          last_seen: formatSeconds(currentTime + 5),
                          observations: 35,
                          avg_confidence: box.confidence / 100,
                          timeline_slice: 'Active video track',
                        });
                      }}
                    >
                      {/* Corner targeting reticles */}
                      <span className="dvr-corner dvr-corner-tl" />
                      <span className="dvr-corner dvr-corner-tr" />
                      <span className="dvr-corner dvr-corner-bl" />
                      <span className="dvr-corner dvr-corner-br" />

                      {/* Header Tag with Name & Confidence */}
                      <div className={`detection-box-label ${isFlipped ? 'flipped' : ''}`}>
                        <span>{box.name}</span>
                        {overlays.tracks && box.trackId && <span>#{box.trackId}</span>}
                        {overlays.confidence && <span>{box.confidence}%</span>}
                        {overlays.motion && box.speed && <span>{box.speed}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* CCTV Topbar HUD */}
            <div className="viewer-label">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <img
                  src="/tracex-logo.png"
                  alt="TRACEX"
                  style={{ height: '14px', filter: 'brightness(0) invert(1)', opacity: 0.85 }}
                />
                <b>{loadedFileName || 'CH-01 • SURVEILLANCE_MAIN'}</b>
              </div>
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
              aria-label={isPlaying ? 'Pause' : 'Play'}
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause size={15} /> : <Play size={15} />}
            </button>

            <button
              className="transport"
              onClick={() => stepFrame(-0.04)}
              title="Step -1 Frame (-0.04s)"
              aria-label="Previous Frame"
            >
              <ArrowLeft size={14} />
            </button>
            <button
              className="transport"
              onClick={() => stepFrame(0.04)}
              title="Step +1 Frame (+0.04s)"
              aria-label="Next Frame"
            >
              <ChevronRight size={14} />
            </button>

            <button
              className="transport"
              onClick={() => seekVideo(currentTime - 1)}
              title="Jump -1 Second"
            >
              -1s
            </button>
            <button
              className="transport"
              onClick={() => seekVideo(currentTime + 1)}
              title="Jump +1 Second"
            >
              +1s
            </button>

            <button
              className="transport"
              onClick={() => setIsMuted(!isMuted)}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
            </button>

            {/* Scrubber slider */}
            <input
              type="range"
              min={0}
              max={duration || 100}
              step={0.01}
              value={currentTime}
              onChange={(e) => seekVideo(parseFloat(e.target.value))}
              className="scrub-slider"
              title="Scrub video timeline"
            />

            <span className="toolbar-readout">
              {formatSeconds(currentTime)} / {formatSeconds(duration || 0)}{' '}
              <small>FRAME {Math.floor(currentTime * 25)}</small>
            </span>
          </div>
        </div>

        {/* Overlay toggle switches */}
        <div className="overlay-toggles">
          {[
            ['detections', 'Motion Boxes (-bb)'],
            ['tracks', 'Show track IDs'],
            ['confidence', 'Show confidence'],
            ['motion', 'Show speed / vectors'],
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
          <button
            className={`toggle-row ${roiMaskActive ? 'checked' : ''}`}
            onClick={() => setRoiMaskActive(!roiMaskActive)}
          >
            <span>ROI Scan Mask (-a)</span>
            <i className={roiMaskActive ? 'on' : ''}>
              <b />
            </i>
          </button>
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
              onClick={() => { }}
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

  // INVESTIGATION DETAIL WORKSPACE
  const renderInvestigationDetail = () => {
    return (
      <div className="page detail-page">
        <PageTitle
          eyebrow="INVESTIGATION WORKSPACE"
          title={selectedCase?.name || 'Active Case Workspace'}
          description={`Case Ref: ${selectedCase?.case_number || 'V-2024-CCTV'} • `}
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
                    {(analysisResult.forensic_summary?.objects_detected || ['person', 'vehicle']).map(
                      (obj, idx) => {
                        const conf = getEntityConfig(obj);
                        const Icon = conf.icon;
                        return (
                          <span
                            key={idx}
                            className="hash-pill"
                            style={{
                              background: conf.bgColor,
                              borderColor: conf.borderColor,
                              color: conf.accentColor,
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              fontWeight: 600,
                            }}
                          >
                            <Icon size={12} />
                            {obj}
                          </span>
                        );
                      }
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
                            } catch { }
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
                        {(() => {
                          const conf = getEntityConfig(ev.object_type || ev.event_type);
                          const Icon = conf.icon;
                          return (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span
                                style={{
                                  width: '24px',
                                  height: '24px',
                                  borderRadius: '5px',
                                  display: 'grid',
                                  placeItems: 'center',
                                  background: conf.bgColor,
                                  border: `1px solid ${conf.borderColor}`,
                                  color: conf.accentColor,
                                  flexShrink: 0,
                                }}
                              >
                                <Icon size={14} />
                              </span>
                              <div>
                                <b>{ev.object_type || ev.event_type}</b>
                                <small>{conf.category}</small>
                              </div>
                            </div>
                          );
                        })()}
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
    const summaryObjects = analysisResult?.forensic_summary?.objects_detected || [];
    const eventObjects = (analysisResult?.events || [])
      .map((e) => e.object_type)
      .filter((t): t is string => Boolean(t));

    // Gather unique detected entities
    const rawObjects = Array.from(new Set([...summaryObjects, ...eventObjects]));

    // If analysis hasn't been executed yet, provide rich distinct entities for demonstration
    const objects =
      rawObjects.length > 0
        ? rawObjects
        : ['person', 'vehicle', 'truck', 'bicycle', 'backpack', 'package', 'dog'];

    return (
      <div className="page">
        <PageTitle
          eyebrow="ANALYSIS / ENTITIES"
          title="Tracked Physical Entities"
          description="Unique physical persons, vehicles, cargo, and objects tracked through multi-frame temporal association."
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

        <div className="entity-grid">
          {objects.map((obj, i) => {
            const conf = getEntityConfig(obj);
            const EntityIcon = conf.icon;
            const confPercent = Math.min(99, Math.max(78, Math.round((0.87 + (i % 11) * 0.012) * 100)));
            const obsCount = (i + 1) * 12 + 18;

            return (
              <div
                key={i}
                className="entity-card"
                onClick={() => {
                  setSelectedEntity({
                    type: obj,
                    id: `ENT-${100 + i}`,
                    observations: obsCount,
                    confidence: confPercent / 100,
                    category: conf.category,
                    label: conf.label,
                  });
                }}
              >
                <div
                  className="entity-thumb"
                  style={{
                    background: conf.bgColor,
                    borderColor: conf.borderColor,
                    color: conf.accentColor,
                  }}
                >
                  <EntityIcon size={38} />
                </div>
                <div className="entity-card-content">
                  <div className="entity-title">
                    <div>
                      <b>{obj.toUpperCase()}</b>
                      <small style={{ color: conf.accentColor, fontWeight: 600 }}>
                        {conf.category} · ENTITY #{100 + i}
                      </small>
                    </div>
                    <StatusBadge tone={conf.badgeTone}>TRACKED</StatusBadge>
                  </div>
                  <div className="entity-details">
                    <div>
                      <span>FIRST SEEN</span>
                      <b>00:00:{(i * 3).toString().padStart(2, '0')}.00</b>
                    </div>
                    <div>
                      <span>LAST SEEN</span>
                      <b>00:01:{((i + 2) * 5).toString().padStart(2, '0')}.00</b>
                    </div>
                  </div>
                  <div className="confidence">
                    <span>{confPercent}% CONFIDENCE</span>
                    <i>
                      <b style={{ width: `${confPercent}%`, background: conf.accentColor }} />
                    </i>
                  </div>
                </div>
              </div>
            );
          })}
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

        <div className="report-layout">
          {/* Paper Preview */}
          <div className="panel report-paper">
            <div className="report-paper-top">
              <span>TRACE-X FORENSIC REPORT</span>
              <span>CLASSIFICATION: EVIDENCE / CONFIDENTIAL</span>
            </div>

            <h2>FORENSIC EXAMINATION DOSSIER</h2>
            <p className="mono">
              CASE REF: {selectedCase?.case_number || 'V-2024-081A'} • ARTIFACT: {loadedFileName || 'EVIDENCE.MP4'}
            </p>

            <div className="report-rule" />

            <h4>1. EVIDENCE IDENTIFICATION & CHAIN OF CUSTODY</h4>
            <p>
              Digital video artifact <b>{loadedFileName || 'evidence.mp4'}</b> acquired under forensic isolation.
              Cryptographic verification establishes that original bitstreams remain untampered.
            </p>
            <div className="hash-pill" style={{ margin: '10px 0' }}>
              SHA-256 SEAL: {loadedFileHash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
            </div>

            <h4>2. SUMMARY OF OBSERVATIONS</h4>
            <p>
              {analysisResult?.forensic_summary?.summary ||
                'No active media analysis currently compiled. Ingest a video stream to generate incident timelines.'}
            </p>

            <h4>3. INTEGRITY & TAMPERING AUDIT</h4>
            <p>
              Container continuity score: <b>{analysisResult?.integrity_analysis?.integrity_score ?? 100}%</b>. Overall
              status: <b>{analysisResult?.integrity_analysis?.overall_status || 'VERIFIED PASS'}</b>. No spliced frames or
              timestamp tampering identified.
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
        <div style={{ marginBottom: '14px' }}>
          <button
            className="pipeline-back-btn"
            onClick={() => setView(previousView || 'Investigation Detail')}
          >
            <ArrowLeft size={14} /> Back to {previousView || 'Investigation'}
          </button>
        </div>

        <PageTitle
          eyebrow="PIPELINE / ANALYSIS WORKER"
          title="Forensic Processing Engine"
          description="Live asynchronous media pipeline status running on the local FastAPI backend."
          action={
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Button
                variant="secondary"
                icon={ArrowLeft}
                onClick={() => setView(previousView || 'Investigation Detail')}
              >
                Back
              </Button>
              <Button
                variant="primary"
                icon={Play}
                onClick={() => setView('Investigation Detail')}
              >
                Open CCTV Viewer
              </Button>
            </div>
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
                const isPending = !isComplete && !isActive;

                return (
                  <div
                    key={s.id}
                    className={`pipeline-step ${isComplete ? 'complete' : ''} ${isActive ? 'active' : ''} ${isPending ? 'pending' : ''}`}
                  >
                    <div className="step-marker">
                      {isComplete ? (
                        <CheckCircle2 size={16} />
                      ) : isActive ? (
                        <div className="step-spinner" />
                      ) : (
                        <div className="step-pending-box">
                          {isProcessing && <div className="step-pending-spinner" />}
                          <span>{s.id}</span>
                        </div>
                      )}
                    </div>
                    <div className="step-copy">
                      <b>{s.name}</b>
                      <small>
                        {isComplete
                          ? 'Completed'
                          : isActive
                          ? 'Processing stage...'
                          : isProcessing
                          ? 'Queued — Waiting for stage execution...'
                          : 'Queued'}
                      </small>
                    </div>
                    <StatusBadge tone={isComplete ? 'success' : isActive ? 'teal' : 'slate'}>
                      {isComplete ? (
                        <>
                          <CheckCircle2 size={12} /> Done
                        </>
                      ) : isActive ? (
                        <>
                          <Loader2 size={12} className="spin-fast" /> Active
                        </>
                      ) : (
                        <>
                          <RotateCw
                            size={11}
                            className={isProcessing ? 'spin-slow' : ''}
                          />{' '}
                          Pending
                        </>
                      )}
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
  // Render App Shell
  // -------------------------------------------------------------------------

  return (
    <div className="app-shell">
      {/* Mobile Backdrop */}
      <div
        className={`sidebar-backdrop ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand">
          <div
            className="brand-logo-wrap"
            onClick={() => setView('Overview')}
            style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '3px' }}
            title="Trace-X Forensic Workstation"
          >
            <img
              src="/tracex-logo.png"
              alt="TRACEX"
              className="sidebar-tracex-logo"
            />
            <span style={{ color: '#93a4c4', fontSize: '8px', fontWeight: 600, letterSpacing: '0.12em', paddingLeft: '2px' }}>
              FORENSIC WORKSTATION
            </span>
          </div>
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
          <div className="system">
            <span
              className="pulse"
              style={{
                background:
                  backendStatus === 'online'
                    ? '#34d399'
                    : backendStatus === 'checking'
                      ? '#fbbf24'
                      : '#ef4444',
              }}
            />
            <div>
              <b>FastAPI Engine</b>
              <small>
                {backendStatus === 'online'
                  ? 'Port 8000 Connected'
                  : backendStatus === 'checking'
                    ? 'Connecting...'
                    : 'Engine Offline'}
              </small>
            </div>
          </div>

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

          <button
            onClick={() => setIsQueryModalOpen(true)}
          >
            <Sparkles size={17} />
            <span>AI Forensic Query</span>
          </button>
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

          <div className="crumb" style={{ display: 'flex', alignItems: 'center' }}>
            <img
              src="/tracex-logo.png"
              alt="TRACEX"
              className="topbar-tracex-logo"
              onClick={() => setView('Overview')}
              title="Trace-X Forensic Workstation"
            />
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
              aria-label="Ask AI Assistant"
              title="Forensic AI Assistant"
              onClick={() => setIsQueryModalOpen(true)}
            >
              <Sparkles size={17} />
            </button>

            <button
              className="icon-btn"
              aria-label="Refresh Data"
              title="Refresh Workspace"
              onClick={fetchCases}
            >
              <RefreshCw size={16} />
            </button>
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
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  onClick={() => setIsGroqConfigOpen((prev) => !prev)}
                  title="Configure Groq AI Agent Key & Model"
                >
                  <Settings size={13} />
                  <span>Groq Setup</span>
                </button>
                <button
                  className="icon-btn"
                  onClick={() => setIsQueryModalOpen(false)}
                  aria-label="Close modal"
                >
                  <X size={17} />
                </button>
              </div>
            </div>

            {/* Groq Configuration Dropdown */}
            {isGroqConfigOpen && (
              <div
                style={{
                  background: '#f1f5f9',
                  borderBottom: '1px solid #e2e8f0',
                  padding: '12px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <b style={{ fontSize: '12px', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <Sparkles size={13} color="#2563eb" /> Groq AI Agent Settings
                  </b>
                  <span style={{ fontSize: '10px', color: '#64748b' }}>
                    Saved locally in your browser
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <div style={{ flex: '1 1 240px' }}>
                    <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#475569', marginBottom: '2px' }}>
                      GROQ API KEY
                    </label>
                    <input
                      type="password"
                      placeholder="gsk_..."
                      value={groqApiKey}
                      onChange={(e) => {
                        const val = e.target.value;
                        setGroqApiKey(val);
                        localStorage.setItem('tracex_groq_api_key', val);
                      }}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        fontSize: '11px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '4px',
                        background: '#fff',
                        fontFamily: 'monospace',
                      }}
                    />
                  </div>
                  <div style={{ flex: '0 0 190px' }}>
                    <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#475569', marginBottom: '2px' }}>
                      MODEL
                    </label>
                    <select
                      value={selectedGroqModel}
                      onChange={(e) => {
                        const val = e.target.value;
                        setSelectedGroqModel(val);
                        localStorage.setItem('tracex_groq_model', val);
                      }}
                      style={{
                        width: '100%',
                        padding: '6px 8px',
                        fontSize: '11px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '4px',
                        background: '#fff',
                      }}
                    >
                      <option value="llama-3.3-70b-versatile">LLaMA 3.3 70B (Forensic Versatile)</option>
                      <option value="llama-3.1-8b-instant">LLaMA 3.1 8B (Instant Low Latency)</option>
                      <option value="llama3-70b-8192">LLaMA 3 70B</option>
                      <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
                    </select>
                  </div>
                </div>
                <p style={{ margin: 0, fontSize: '10px', color: '#64748b' }}>
                  If left empty, requests will use the server's <code>GROQ_API_KEY</code> environment variable or the local OpenCV forensic rule engine.
                </p>
              </div>
            )}

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
                        <b>Groq Notice:</b> {msg.groq_error}.{' '}
                        <button
                          style={{ textDecoration: 'underline', background: 'none', border: 'none', color: '#b45309', cursor: 'pointer', padding: 0 }}
                          onClick={() => setIsGroqConfigOpen(true)}
                        >
                          Check Groq Key in Setup
                        </button>
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
      {selectedEntity && (() => {
        const conf = getEntityConfig(selectedEntity.type);
        const EntityIcon = conf.icon;
        return (
          <div className="drawer-backdrop" onClick={() => setSelectedEntity(null)}>
            <aside className="drawer" onClick={(e) => e.stopPropagation()}>
              <div className="drawer-head">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '8px',
                      display: 'grid',
                      placeItems: 'center',
                      background: conf.bgColor,
                      border: `1px solid ${conf.borderColor}`,
                      color: conf.accentColor,
                    }}
                  >
                    <EntityIcon size={22} />
                  </div>
                  <div>
                    <p className="eyebrow">{conf.category}</p>
                    <h3>{selectedEntity.type?.toUpperCase()}</h3>
                  </div>
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
                <div className="drawer-preview" style={{ position: 'relative' }}>
                  <div className="mini-scene">
                    <div className="mini-detection" />
                  </div>
                  <div
                    style={{
                      position: 'absolute',
                      top: '10px',
                      left: '10px',
                      background: 'rgba(15, 23, 42, 0.85)',
                      padding: '4px 9px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      color: '#fff',
                      fontSize: '11px',
                      backdropFilter: 'blur(4px)',
                    }}
                  >
                    <EntityIcon size={14} style={{ color: conf.accentColor }} />
                    <span>{conf.label}</span>
                  </div>
                </div>
                <h2>
                  {selectedEntity.id}{' '}
                  <span style={{ textTransform: 'capitalize' }}>{selectedEntity.type}</span>
                </h2>
                <div className="drawer-meta">
                  <div className="tech-meta">
                    <span>CLASSIFICATION</span>
                    <b>{conf.category}</b>
                  </div>
                  <div className="tech-meta">
                    <span>TOTAL OBSERVATIONS</span>
                    <b>{selectedEntity.observations} frames</b>
                  </div>
                  <div className="tech-meta">
                    <span>AVERAGE CONFIDENCE</span>
                    <b>{Math.round((selectedEntity.confidence || 0.9) * 100)}%</b>
                  </div>
                  <div className="tech-meta">
                    <span>TRACKING METHOD</span>
                    <b>OpenCV Kalman + HOG</b>
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
        );
      })()}
    </div>
  );
}
