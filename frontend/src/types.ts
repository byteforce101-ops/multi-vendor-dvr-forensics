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

export interface VideoAnalysisEvent {
  event_type: string;
  video_id: string;
  camera_id: string;
  start_time: string;
  end_time: string;
  confidence: number | null;
  track_id: string | null;
  object_type: string | null;
  metadata?: Record<string, unknown>;
}

export interface VideoAnalysisMetadata {
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  codec: string | null;
  format: string | null;
  pixel_format: string | null;
  frame_count: number | null;
  has_audio: boolean;
}

export interface VideoAnalysisResult {
  status: string;
  analysis_id: string;
  filename: string;
  video_path: string;
  metadata: VideoAnalysisMetadata;
  frames_analyzed: number;
  event_count: number;
  events: VideoAnalysisEvent[];
  timeline_count: number;
  timeline: Array<Record<string, unknown>>;
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
  codeLines: Array<{ label: string; value: string }>;
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
