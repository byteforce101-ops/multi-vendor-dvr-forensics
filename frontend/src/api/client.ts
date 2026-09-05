import { supabase, isSupabaseConfigured } from '../lib/supabase';

export const API_BASE = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL
  || 'http://127.0.0.1:8000';

export async function getAuthHeaders(): Promise<HeadersInit> {
  if (!isSupabaseConfigured || !supabase) return {};
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = { ...(await getAuthHeaders()), ...(init.headers || {}) };
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? (typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)) : detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(`${res.status}: ${detail}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

function jsonInit(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

// ---------------------------------------------------------------------------
// Types (mirror backend/db/schemas.py)
// ---------------------------------------------------------------------------

export interface CaseSummary {
  id: string;
  name: string;
  investigator: string;
  case_number: string | null;
  description: string | null;
  status: string;
  created_at: string;
}

export interface RecordingSummary {
  id: string;
  camera_id: string;
  recording_identifier: string;
  extracted_path: string | null;
  original_timestamp: string | null;
  normalized_timestamp: string | null;
  duration_seconds: number | null;
  resolution: string | null;
  fps: number | null;
  codec: string | null;
  file_size: number | null;
  recovery_status: string;
}

export interface EvidenceSummary {
  id: string;
  case_id: string;
  original_filename: string;
  sha256: string | null;
  md5: string | null;
  status: string;
  acquired_at: string;
  vendor: string | null;
  parser_version: string | null;
  parse_warnings: string[];
  parse_errors: string[];
  recordings: RecordingSummary[];
}

export interface ForensicEvent {
  id: string;
  evidence_id: string;
  recording_id: string | null;
  case_id: string;
  camera_id: string;
  event_type: string;
  start_time: string;
  end_time: string;
  confidence: number | null;
  track_id: string | null;
  object_type: string | null;
}

export interface AnalyzeResponse {
  events: ForensicEvent[];
  errors: Array<{ recording_id: string; error: string }>;
}

export interface SearchResponse {
  query: string;
  filter: Record<string, unknown>;
  results: ForensicEvent[];
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

import type { VideoAnalysisResult } from '../types';

export const api = {
  checkHealth: () => request<{ status: string; service: string; timestamp: string }>('/health'),

  listCases: () => request<CaseSummary[]>('/cases'),

  createCase: (name: string, investigator = 'Enterprise User', description = '', case_number = '') =>
    request<CaseSummary>('/cases', jsonInit('POST', { name, investigator, description, case_number })),

  getCase: (caseId: string) => request<CaseSummary>(`/cases/${caseId}`),

  uploadEvidence: (caseId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    // Do not set Content-Type manually — the browser sets the multipart
    // boundary for us when the body is a FormData instance.
    return request<EvidenceSummary>(`/cases/${caseId}/evidence/upload`, { method: 'POST', body: form });
  },

  listEvidence: (caseId: string) => request<EvidenceSummary[]>(`/cases/${caseId}/evidence`),

  getEvidence: (evidenceId: string) => request<EvidenceSummary>(`/evidence/${evidenceId}`),

  parseEvidence: (evidenceId: string) =>
    request<EvidenceSummary>(`/evidence/${evidenceId}/parse`, { method: 'POST' }),

  extractEvidence: (evidenceId: string) =>
    request<EvidenceSummary>(`/evidence/${evidenceId}/extract`, { method: 'POST' }),

  analyzeEvidence: (evidenceId: string) =>
    request<AnalyzeResponse>(`/evidence/${evidenceId}/analyze`, { method: 'POST' }),

  getCaseEvents: (caseId: string) => request<ForensicEvent[]>(`/cases/${caseId}/events`),

  searchCase: (caseId: string, query: string) =>
    request<SearchResponse>(`/cases/${caseId}/search`, jsonInit('POST', { query })),

  analyzeVideo: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<VideoAnalysisResult>('/video/analyze', { method: 'POST', body: form });
  },

  queryVideo: (
    query: string,
    events: unknown[] = [],
    summary: unknown = null,
    extra: {
      integrity?: unknown;
      disappearances?: unknown[];
      groqApiKey?: string;
      model?: string;
      chatHistory?: Array<{ sender: string; text: string }>;
    } = {}
  ) =>
    request<{
      answer: string;
      matching_events: unknown[];
      source: string;
      model?: string;
      groq_error?: string;
    }>(
      '/video/query',
      jsonInit('POST', {
        query,
        events,
        summary,
        integrity: extra.integrity,
        disappearances: extra.disappearances,
        groq_api_key: extra.groqApiKey,
        model: extra.model,
        chat_history: extra.chatHistory,
      })
    ),

  getVideoStreamUrl: (analysisId: string) => `${API_BASE}/video/${analysisId}/stream`,
};