export interface PipelineStep {
  id: number;
  label: string;
  shortName?: string;
  status: 'completed' | 'active' | 'pending';
  description: string;
}

export interface EvidenceFile {
  id: string;
  name: string;
  caseId: string;
  size: string;
  rawSizeBytes?: number;
  sourceFile?: File;
  uploadedAt: string;
  hash: string;
  status: 'verified' | 'processing' | 'queued' | 'error';
  codec?: string;
  duration?: string;
  resolution?: string;
  telemetry?: {
    gps?: string;
    bitrate?: string;
    fps?: number;
    audioChannels?: number;
  };
}

export interface ActivityLogItem {
  id: string;
  timestamp: string;
  action: string;
  fileName: string;
  caseId: string;
  hashSnippet: string;
  operator: string;
  verified: boolean;
}

export interface ArchitectureCardItem {
  id: string;
  title: string;
  description: string;
  iconType: 'fingerprint' | 'parse' | 'analysis';
  iconColor: string;
  codeLines: Array<{
    label: string;
    value: string;
  }>;
}

export interface SupabaseUser {
  id: string;
  email: string;
  role: string;
  enterpriseId: string;
  name: string;
  isLoggedIn: boolean;
  avatarUrl?: string;
}

/* =========================================================
   AI FORENSIC RECONSTRUCTION
   ========================================================= */

export interface ReconstructedForensicEvent {
  video_id: string;
  camera_id: string;
  event_type: string;
  start_time: string;
  end_time: string;
  title: string;
  description: string;
  objects: string[];
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface ForensicSummary {
  video_id: string;
  camera_id: string;
  start_time: string | null;
  end_time: string | null;
  headline: string;
  summary: string;
  key_events: string[];
  objects_detected: string[];
  event_count: number;
  confidence: number;
  metadata: Record<string, unknown>;
}

/* =========================================================
   VIDEO INTEGRITY / TAMPERING
   ========================================================= */

export interface VideoIntegrityAnalysis {
  available: boolean;
  error?: string;

  timestamp_continuity: boolean;
  frame_continuity: boolean;
  fps_consistency: boolean;
  duplicate_frames: boolean;
  metadata_consistency: boolean;
  resolution_consistency: boolean;
  compression_consistency: boolean;

  frames_checked: number;
  timestamp_gaps: number;
  duplicate_sequences: number;
  corrupted_frames: number;
  fps_changes: number;
  resolution_changes: number;
  compression_changes: number;

  details: Record<string, unknown>;
  anomalies: string[];

  integrity_score: number;
  overall_status: 'PASS' | 'WARNING' | 'ERROR' | string;
}

/* =========================================================
   OBJECT DISAPPEARANCE DETECTION
   ========================================================= */

export interface ObjectDisappearance {
  camera_id: string;
  object_type: string;
  first_seen: string;
  last_seen: string;
  disappearance_time: string;
  observation_count: number;
  related_activity: string[];
}

export interface ObjectDisappearanceAnalysis {
  available: boolean;
  count: number;
  disappearances: ObjectDisappearance[];
  note: string;
}

export interface VideoAnalysisResult {
  video_integrity?: any;
  status?: string;
  analysis_id: string;
  filename?: string;

  metadata: {
    duration_seconds?: number | null;
    duration?: number | null;
    width: number | null;
    height: number | null;
    fps: number | null;
    codec: string | null;
    has_audio?: boolean;
    format_name?: string;
    bitrate?: number;
  };

  frames_analyzed?: number;
  event_count?: number;

  events: Array<{
    event_type: string;
    video_id?: string;
    camera_id: string;
    start_time: string;
    end_time: string;
    confidence: number | null;
    track_id: number | null;
    object_type: string | null;
    start_seconds?: number;
    end_seconds?: number;
    bbox?: any;
    metadata: Record<string, any>;
  }>;

  reconstructed_events?: ReconstructedForensicEvent[];
  reconstruction_count?: number;
  forensic_summary?: any;

  /* Video integrity / tampering analysis */
  integrity_analysis?: any;

  /* Object disappearance analysis */
  object_disappearance_analysis?: any;
}
