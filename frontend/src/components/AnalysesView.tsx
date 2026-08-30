import React, { useState, useRef } from 'react';
import {
  Play,
  Pause,
  Download,
  Activity,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Film,
  CheckCircle2,
  ChevronRight,
  MessageSquare,
  Send,
  Sparkles,
  Bot,
  User,
  EyeOff,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { VideoAnalysisResult } from '../types';
import { API_BASE, getAuthHeaders } from '../api/client';

interface AnalysesViewProps {
  analysis?: VideoAnalysisResult | null;
  videoUrl?: string | null;
}

const formatEventTime = (value?: string | null) => {
  if (!value) return '--:--:--';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toISOString().slice(11, 23);
};

const formatDuration = (seconds: number | null | undefined) => {
  if (seconds == null || Number.isNaN(seconds)) return '--:--:--';
  const wholeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(wholeSeconds / 3600);
  const minutes = Math.floor((wholeSeconds % 3600) / 60);
  const remainder = wholeSeconds % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${remainder.toString().padStart(2, '0')}`;
};

const formatConfidence = (conf?: number | null) => {
  if (conf == null || Number.isNaN(conf)) return '—';
  const val = conf <= 1 ? conf * 100 : conf;
  return `${Math.round(val)}%`;
};

export const AnalysesView: React.FC<AnalysesViewProps> = ({
  analysis,
  videoUrl,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeTab, setActiveTab] = useState<'video' | 'events' | 'reconstruction' | 'integrity' | 'disappearance' | 'query'>('video');
  const [selectedEventType, setSelectedEventType] = useState<string>('ALL');

  // Conversational Video Q&A (CLI interactive mode integration)
  const [queryInput, setQueryInput] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{ sender: 'user' | 'assistant'; text: string; events?: any[] }>>([
    {
      sender: 'assistant',
      text: 'Hello! I am your AI forensic analysis assistant. You can ask questions about this video like: "Did anyone enter after 10pm?", "What vehicles were seen?", "Did any object disappear?", or "Show all motion alerts".',
    },
  ]);

  const videoRef = useRef<HTMLVideoElement>(null);

  const duration = analysis?.metadata?.duration_seconds ?? 0;
  const events = analysis?.events ?? [];

  const getTimestampSeconds = (
    timeString?: string | null,
    metadata?: Record<string, unknown>,
    firstEventTime?: string | null,
    fallbackSeconds: number = 0
  ): number => {
    if (metadata?.timestamp_seconds != null && typeof metadata.timestamp_seconds === 'number') {
      return Math.max(0, metadata.timestamp_seconds);
    }
    if (metadata?.seconds != null && typeof metadata.seconds === 'number') {
      return Math.max(0, metadata.seconds);
    }
    if (timeString && firstEventTime) {
      const t0 = new Date(firstEventTime).getTime();
      const t1 = new Date(timeString).getTime();
      if (!isNaN(t0) && !isNaN(t1) && t1 >= t0) {
        const deltaSec = (t1 - t0) / 1000;
        if (duration > 0 && deltaSec > duration) {
          return Math.min(deltaSec % duration, duration);
        }
        return deltaSec;
      }
    }
    if (duration > 0) {
      return Math.min(fallbackSeconds, duration);
    }
    return fallbackSeconds;
  };

  const filteredEvents = events.filter((ev) => {
    if (selectedEventType === 'ALL') return true;
    if (selectedEventType === 'PERSON') return ev.object_type?.toLowerCase().includes('person') || ev.event_type.toLowerCase().includes('person');
    if (selectedEventType === 'VEHICLE') return ev.object_type?.toLowerCase().includes('car') || ev.object_type?.toLowerCase().includes('truck') || ev.object_type?.toLowerCase().includes('vehicle');
    if (selectedEventType === 'MOTION') return ev.event_type.toLowerCase().includes('motion');
    if (selectedEventType === 'REVIEW') return ev.event_type.startsWith('REVIEW_FLAG_') || ev.event_type.includes('PROXIMITY') || ev.event_type.includes('STOP');
    return true;
  });

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play().catch(() => {});
      }
      setIsPlaying(!isPlaying);
    }
  };

  const seekToTime = (timeInSeconds: number) => {
    if (videoRef.current) {
      const boundedTime = duration > 0 ? Math.min(Math.max(0, timeInSeconds), duration) : Math.max(0, timeInSeconds);
      videoRef.current.currentTime = boundedTime;
      setCurrentTime(boundedTime);
      if (!isPlaying) {
        videoRef.current.play().catch(() => {});
        setIsPlaying(true);
      }
    }
  };

  const handleExportJSON = () => {
    if (!analysis) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(analysis, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `tracex-forensic-dossier-${analysis.analysis_id || String(Date.now())}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleSendQuery = async (queryText: string) => {
    const q = queryText.trim();
    if (!q || isQuerying) return;

    setChatMessages((prev) => [...prev, { sender: 'user', text: q }]);
    setQueryInput('');
    setIsQuerying(true);

    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${API_BASE}/video/query`, {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: q,
          events: analysis?.events || [],
          summary: analysis?.forensic_summary || {},
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setChatMessages((prev) => [
          ...prev,
          {
            sender: 'assistant',
            text: data.answer,
            events: data.matching_events,
          },
        ]);
      } else {
        throw new Error('Query request failed');
      }
    } catch {
      // Local intelligent fallback
      const qLower = q.toLowerCase();
      const matched = events.filter((ev) => {
        const type = (ev.event_type || '').toLowerCase();
        const obj = (ev.object_type || '').toLowerCase();
        if (qLower.includes('person') && (type.includes('person') || obj.includes('person'))) return true;
        if (qLower.includes('vehicle') && (type.includes('vehicle') || obj.includes('vehicle') || obj.includes('car'))) return true;
        if (qLower.includes('motion') && type.includes('motion')) return true;
        if (qLower.includes('disappear') && type.includes('disappearance')) return true;
        return false;
      });

      let reply = '';
      if (matched.length > 0) {
        reply = `Found ${matched.length} event(s) matching "${q}". The first occurrence was logged at ${formatEventTime(matched[0].start_time)}. Click the event badge below to review that point in the stream.`;
      } else {
        reply = `No matching events detected for "${q}" in the current frame log. Total analyzed events: ${events.length}.`;
      }

      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: reply,
          events: matched.slice(0, 5),
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  const integrity = analysis?.integrity_analysis || (analysis as any)?.video_integrity;
  const disappearances =
    analysis?.object_disappearance_analysis?.disappearances ||
    (analysis as any)?.object_disappearance?.disappearances ||
    [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-6"
    >
      {/* Top Header & Export */}
      <div className="spotlight-card p-6 sm:p-7 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="shimmer-badge text-[11px] font-semibold px-2.5 py-0.5 rounded-full text-indigo-900 border border-indigo-200/80">
              Analysis #{analysis?.analysis_id ? analysis.analysis_id.slice(0, 8) : 'ACTIVE'}
            </span>
            <span className="text-xs text-slate-500 font-medium truncate">
              {analysis?.filename || 'evidence.mp4'}
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-1.5">
            Forensic Intelligence Workspace
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {analysis?.frames_analyzed ?? 0} frames dissected • {analysis?.event_count ?? 0} chronological detections • {analysis?.reconstruction_count ?? 0} reconstructed activity incidents
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleExportJSON}
            className="btn-kinetic-primary px-4 py-2 text-xs font-semibold tracking-wide flex items-center gap-2 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Certified Dossier (JSON)</span>
          </motion.button>
        </div>
      </div>

      {/* Action Buttons Bar / React Bits Animated Sliding Tabs */}
      <div className="bg-slate-100/80 p-1.5 rounded-2xl border border-slate-200/80 flex flex-wrap items-center gap-1">
        {[
          { id: 'video', label: 'Video Player', icon: Film },
          { id: 'events', label: 'Event Chronology', icon: Clock, badge: events.length },
          { id: 'reconstruction', label: 'Activity Reconstruction', icon: Activity, badge: analysis?.reconstruction_count },
          { id: 'integrity', label: 'Stream Integrity', icon: ShieldCheck, status: integrity?.overall_status },
          { id: 'disappearance', label: 'Object Disappearance', icon: EyeOff, badge: disappearances.length },
          { id: 'query', label: 'Ask About Video', icon: MessageSquare, highlight: true },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`relative flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-colors cursor-pointer select-none ${
                isActive
                  ? 'text-white font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
              }`}
            >
              {/* React Bits: Animated Spring Pill Layout */}
              {isActive && (
                <motion.div
                  layoutId="activeTabPill"
                  transition={{ type: 'spring', stiffness: 450, damping: 35 }}
                  className="absolute inset-0 bg-slate-900 rounded-xl shadow-xs"
                />
              )}

              <span className="relative z-10 flex items-center gap-2">
                <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-indigo-300' : 'text-indigo-600'}`} />
                <span>{tab.label}</span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    isActive ? 'bg-indigo-500/30 text-indigo-200' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {tab.badge}
                  </span>
                )}
                {tab.status && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    tab.status === 'PASS'
                      ? isActive
                        ? 'bg-emerald-500/30 text-emerald-200'
                        : 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-900'
                  }`}>
                    {tab.status}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT WITH ANIMATED TRANSITIONS */}
      <AnimatePresence mode="wait">
        {/* 1. VIDEO PLAYER & METADATA */}
        {activeTab === 'video' && (
          <motion.div
            key="video"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-6"
          >
            <div className="lg:col-span-8 spotlight-card overflow-hidden">
              <div className="relative bg-slate-950 aspect-video flex items-center justify-center">
                {videoUrl ? (
                  <video
                    ref={videoRef}
                    src={videoUrl}
                    onTimeUpdate={() => {
                      if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
                    }}
                    onEnded={() => setIsPlaying(false)}
                    className="w-full h-full object-contain"
                    controls={false}
                  />
                ) : (
                  <div className="text-center p-8 text-slate-500">
                    <Film className="w-12 h-12 mx-auto text-slate-700 mb-2" />
                    <p className="text-sm font-medium text-slate-400">Direct Video Feed</p>
                    <p className="text-xs text-slate-600 mt-1">Upload a video to view real-time synchronized playback</p>
                  </div>
                )}

                {/* Timecode overlay badge */}
                <div className="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-md text-white px-2.5 py-1 rounded-lg text-xs font-mono border border-white/10 shadow-xs">
                  {formatDuration(currentTime)} / {formatDuration(duration)}
                </div>
              </div>

              {/* Playback Controls Bar */}
              <div className="p-4 border-t border-slate-100 flex items-center justify-between gap-3 bg-white">
                <div className="flex items-center gap-2.5">
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={togglePlay}
                    className="w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center transition-colors cursor-pointer shadow-xs"
                  >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                  </motion.button>
                  <span className="text-xs font-mono text-slate-800 font-semibold">
                    {formatDuration(currentTime)}
                  </span>
                </div>

                <div className="flex-1 mx-4">
                  <input
                    type="range"
                    min={0}
                    max={duration || 100}
                    step={0.1}
                    value={currentTime}
                    onChange={(e) => seekToTime(parseFloat(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  />
                </div>

                <span className="text-xs text-slate-500 font-mono hidden sm:inline">
                  FPS: {analysis?.metadata?.fps || 30}
                </span>
              </div>
            </div>

            {/* Container Metadata Specifications */}
            <div className="lg:col-span-4 spotlight-card p-6 space-y-4">
              <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                Stream & Bitstream Specifications
              </h3>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-500">Codec</span>
                  <span className="font-semibold text-slate-900">{analysis?.metadata?.codec || 'H.264 / AVC'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-500">Resolution</span>
                  <span className="font-semibold text-slate-900">
                    {analysis?.metadata?.width || 1920} × {analysis?.metadata?.height || 1080}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-500">Duration</span>
                  <span className="font-semibold text-slate-900">{formatDuration(duration)}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-500">Sampled Frames</span>
                  <span className="font-semibold text-slate-900">{analysis?.frames_analyzed || 0}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-slate-100">
                  <span className="text-slate-500">Audio Track</span>
                  <span className="font-semibold text-slate-900">{analysis?.metadata?.has_audio ? 'Embedded' : 'None'}</span>
                </div>
              </div>

              {analysis?.forensic_summary && (
                <div className="pt-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600">Forensic Brief</span>
                  <p className="text-xs font-bold text-slate-900 mt-1">{analysis.forensic_summary.headline}</p>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">{analysis.forensic_summary.summary}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* 2. EVENT CHRONOLOGY (MULTI-TRACK TIMELINE) */}
        {activeTab === 'events' && (
          <motion.div
            key="events"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="spotlight-card p-6 space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Event Chronology & Classified Detections
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Frame-by-frame neural bounding boxes and motion differential markers
                </p>
              </div>

              {/* Filter Pills */}
              <div className="flex flex-wrap gap-1.5">
                {['ALL', 'PERSON', 'VEHICLE', 'MOTION', 'REVIEW'].map((type) => (
                  <button
                    key={type}
                    onClick={() => setSelectedEventType(type)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                      selectedEventType === type
                        ? 'bg-slate-900 text-white shadow-xs'
                        : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {filteredEvents.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No events found matching the active filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>Timecode</th>
                      <th>Type</th>
                      <th>Object / Track</th>
                      <th>Confidence</th>
                      <th>Notes</th>
                      <th className="text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEvents.map((ev, idx) => (
                      <tr key={idx} className="hover:bg-indigo-50/20 transition-colors">
                        <td className="font-mono text-xs text-indigo-600 font-semibold whitespace-nowrap">
                          {formatEventTime(ev.start_time)}
                        </td>
                        <td>
                          <span className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                            {ev.event_type}
                          </span>
                        </td>
                        <td className="font-medium text-slate-900">
                          {ev.object_type ? `${ev.object_type} ${ev.track_id ? `(#${ev.track_id})` : ''}` : 'General'}
                        </td>
                        <td>
                          <span className="inline-flex items-center text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                            {formatConfidence(ev.confidence)}
                          </span>
                        </td>
                        <td className="text-slate-600 text-xs truncate max-w-xs">
                          {(ev.metadata as any)?.note || 'Standard detection'}
                        </td>
                        <td className="text-right">
                          <button
                            onClick={() => {
                              const targetSec = getTimestampSeconds(
                                ev.start_time,
                                ev.metadata,
                                events[0]?.start_time,
                                idx * 2
                              );
                              seekToTime(targetSec);
                              setActiveTab('video');
                            }}
                            className="px-2.5 py-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded-lg transition-colors cursor-pointer"
                          >
                            Jump to Video →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </motion.div>
        )}

        {/* 3. ACTIVITY RECONSTRUCTION & FINDINGS */}
        {activeTab === 'reconstruction' && (
          <motion.div
            key="reconstruction"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="spotlight-card p-6 sm:p-7 space-y-5"
          >
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                Automated Activity Reconstruction
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Heuristic correlation grouping low-level frame detections into coherent multi-camera activity narratives
              </p>
            </div>

            {analysis?.reconstructed_events && analysis.reconstructed_events.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.reconstructed_events.map((rec, idx) => (
                  <motion.div
                    key={idx}
                    whileHover={{ y: -2 }}
                    className="p-5 rounded-2xl border border-slate-200 bg-white space-y-3 shadow-xs"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">
                          {rec.event_type.replaceAll('_', ' ')}
                        </span>
                        <h4 className="text-sm font-bold text-slate-900 mt-0.5">{rec.title}</h4>
                      </div>
                      <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                        {formatConfidence(rec.confidence)}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">{rec.description}</p>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                      <span>{formatEventTime(rec.start_time)} → {formatEventTime(rec.end_time)}</span>
                      <span>Objects: {rec.objects.join(', ')}</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="py-10 text-center text-xs text-slate-400">
                No reconstructed high-level activities detected in this footage.
              </div>
            )}
          </motion.div>
        )}

        {/* 4. STREAM INTEGRITY & TAMPERING */}
        {activeTab === 'integrity' && (
          <motion.div
            key="integrity"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="spotlight-card p-6 sm:p-7 space-y-6"
          >
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Stream Integrity & Bitstream Diagnostics
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  PTS/DTS continuity checks, duplicate frame sequences, and splice/tamper detection
                </p>
              </div>

              <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                integrity?.overall_status === 'PASS'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-amber-50 text-amber-900 border border-amber-200'
              }`}>
                STATUS: {integrity?.overall_status || 'PASS'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Integrity Score</span>
                <p className="text-2xl font-extrabold text-slate-900 mt-1">{integrity?.integrity_score ?? 100}%</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Frames Inspected</span>
                <p className="text-2xl font-extrabold text-slate-900 mt-1">{integrity?.frames_checked ?? analysis?.frames_analyzed ?? 0}</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Timestamp Gaps</span>
                <p className="text-2xl font-extrabold text-slate-900 mt-1">{integrity?.timestamp_gaps ?? 0}</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Duplicate Sequences</span>
                <p className="text-2xl font-extrabold text-slate-900 mt-1">{integrity?.duplicate_sequences ?? 0}</p>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              {[
                ['Timestamp continuity scan', integrity?.timestamp_continuity ?? true],
                ['Frame sequence continuity', integrity?.frame_continuity ?? true],
                ['FPS cadence stability', integrity?.fps_consistency ?? true],
                ['Duplicate frame analysis', integrity?.duplicate_frames ?? true],
                ['Metadata & container consistency', integrity?.metadata_consistency ?? true],
              ].map(([label, passed]) => (
                <div key={String(label)} className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-slate-50/40 text-xs">
                  <span className="font-medium text-slate-800">{String(label)}</span>
                  {passed ? (
                    <span className="flex items-center gap-1.5 font-semibold text-emerald-600">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> PASS
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 font-semibold text-amber-700">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> REVIEW
                    </span>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* 5. OBJECT DISAPPEARANCE WATCHLIST */}
        {activeTab === 'disappearance' && (
          <motion.div
            key="disappearance"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="spotlight-card p-6 sm:p-7 space-y-4"
          >
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                Object Disappearance Watchlist
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Tracks stationary objects that ceased to be detected abruptly without motion decay
              </p>
            </div>

            {disappearances.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 bg-slate-50/60 rounded-xl border border-slate-200/80">
                No stationary object disappearance anomalies flagged in this footage.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {disappearances.map((disp: any, idx: number) => {
                  const dispTime = disp.disappearance_time || disp.disappearance_timestamp;
                  const dispCamera = disp.camera_id || 'CH-01';
                  const dispCount = disp.observation_count ?? 1;
                  const dispDesc =
                    disp.context_description ||
                    (disp.related_activity?.length
                      ? `Stationary across ${dispCount} observation(s) in: ${disp.related_activity.join(', ')}`
                      : `Stationary ${disp.object_type} ceased detection abruptly in feed.`);

                  return (
                    <motion.div
                      key={idx}
                      whileHover={{ y: -2 }}
                      className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 text-xs shadow-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 uppercase">
                          {disp.object_type} ({dispCamera})
                        </span>
                        <span className="text-[10px] bg-rose-50 text-rose-700 px-2 py-0.5 rounded-full font-bold border border-rose-200">
                          LOST @ {formatEventTime(dispTime)}
                        </span>
                      </div>
                      <p className="text-slate-600 leading-relaxed">{dispDesc}</p>
                      <div className="pt-1.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                        <span>Seen: {formatEventTime(disp.first_seen)} → {formatEventTime(disp.last_seen)}</span>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}

        {/* 6. ASK ABOUT VIDEO (CLI INTERACTIVE QUERY INTEGRATION) */}
        {activeTab === 'query' && (
          <motion.div
            key="query"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="spotlight-card p-6 sm:p-7 space-y-5"
          >
            <div className="pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Conversational Video Intelligence (CLI Query Engine)
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Ask natural-language questions about this footage (e.g. "Did anyone enter?", "List vehicles seen", "Did any object disappear?")
              </p>
            </div>

            {/* Quick Query Suggestion Chips */}
            <div className="flex flex-wrap gap-2">
              {[
                'Did any person appear in the video?',
                'What vehicles were detected?',
                'Show any motion or suspicious movements',
                'Did any object disappear?',
                'Summarize the timeline chronologically',
              ].map((promptText) => (
                <button
                  key={promptText}
                  onClick={() => handleSendQuery(promptText)}
                  className="text-xs px-3 py-1.5 rounded-full bg-slate-50 hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 font-medium transition-colors cursor-pointer"
                >
                  {promptText}
                </button>
              ))}
            </div>

            {/* Chat Messages Log */}
            <div className="space-y-3 min-h-[240px] max-h-[380px] overflow-y-auto p-4 rounded-2xl bg-slate-50/60 border border-slate-200/80">
              {chatMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex gap-3 text-xs leading-relaxed ${
                    msg.sender === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {msg.sender === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`p-4 rounded-2xl max-w-xl space-y-2 ${
                      msg.sender === 'user'
                        ? 'bg-slate-900 text-white rounded-tr-none shadow-xs'
                        : 'bg-white text-slate-900 border border-slate-200/80 rounded-tl-none shadow-xs'
                    }`}
                  >
                    <p>{msg.text}</p>

                    {/* Matching Event Jump Badges */}
                    {msg.events && msg.events.length > 0 && (
                      <div className="pt-2.5 border-t border-slate-100 space-y-1">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Referenced Timestamps:</span>
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {msg.events.map((ev: any, evIdx: number) => (
                            <button
                              key={evIdx}
                              onClick={() => {
                                const targetSec = getTimestampSeconds(
                                  ev.start_time,
                                  ev.metadata,
                                  events[0]?.start_time,
                                  evIdx * 2
                                );
                                seekToTime(targetSec);
                                setActiveTab('video');
                              }}
                              className="text-[11px] px-2.5 py-0.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 font-mono flex items-center gap-1 cursor-pointer transition-colors"
                            >
                              <span>{ev.event_type || 'EVENT'}</span>
                              <span className="font-bold">@{formatEventTime(ev.start_time || '')}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {msg.sender === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))}

              {isQuerying && (
                <div className="flex gap-3 text-xs justify-start">
                  <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="p-3.5 bg-white text-slate-600 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping" />
                    <span>Querying forensic event chronology...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Query Input Box */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendQuery(queryInput);
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="Ask anything about this video (e.g. 'What happened between 12:00 and 12:15?')"
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 shadow-xs"
              />
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="submit"
                disabled={isQuerying || !queryInput.trim()}
                className="btn-kinetic-primary px-4 py-2.5 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Ask</span>
              </motion.button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
