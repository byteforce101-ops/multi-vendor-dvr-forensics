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
