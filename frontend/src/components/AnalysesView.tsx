import React, { useState } from 'react';
import { Play, Pause, Download } from 'lucide-react';
import { motion } from 'motion/react';
import { ForensicEvent } from '../api/client';

interface AnalysesViewProps {
  caseName: string;
  events: ForensicEvent[];
  loading?: boolean;
}

export const AnalysesView: React.FC<AnalysesViewProps> = ({ caseName, events, loading }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(events[0]?.id ?? null);

  const selected = events.find((e) => e.id === selectedEventId) ?? events[0] ?? null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-7"
    >
      <div className="bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] p-6 sm:p-8 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-mono font-bold text-[#3b5749] uppercase tracking-wider bg-[#eaf1ed] border border-[#c9dcd0] px-3 py-0.5 rounded-md">
            Active Forensic Analysis
          </span>
          <h2 className="text-2xl sm:text-3xl font-['DM_Sans',sans-serif] text-[#221e1b] mt-2 font-normal">
            Case {caseName} • Event Timeline
          </h2>
          <p className="text-xs text-[#6e6459] font-mono mt-1">
            {loading ? 'Loading events…' : `${events.length} detected event(s)`}
          </p>
        </div>
        <button className="btn-primary-navy px-5 py-2.5 rounded-xl text-white text-xs font-semibold flex items-center gap-2 self-start sm:self-auto cursor-pointer">
          <Download className="w-4 h-4" />
          <span>Export Dossier</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] p-6 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] flex flex-col justify-between">
          <div className="relative aspect-video bg-[#141b22] rounded-xl overflow-hidden flex items-center justify-center group shadow-inner">
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30 pointer-events-none" />

            {selected && (
              <div className="absolute top-4 left-4 text-[11px] font-mono text-white/80 pointer-events-none">
                {selected.event_type} [{selected.camera_id}]
              </div>
            )}

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="w-14 h-14 rounded-full bg-white/20 hover:bg-white/35 backdrop-blur-md text-white flex items-center justify-center transition-transform hover:scale-105 cursor-pointer"
            >
              {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-0.5" />}
            </button>

            <div className="absolute bottom-0 left-0 right-0 p-4 flex items-center justify-between text-white text-xs font-mono">
              <span className="text-[#c2593f] font-bold">
                {selected ? new Date(selected.start_time).toLocaleTimeString() : '--:--:--'}
              </span>
              <span className="bg-white/10 px-2 py-0.5 rounded text-[11px]">Video playback wiring pending</span>
            </div>
          </div>
        </div>

        <div className="bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] p-6 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#221e1b] font-['DM_Sans',sans-serif] text-xl">Detected Events</h3>
            <span className="text-xs font-mono text-[#3b5749] bg-[#eaf1ed] px-2.5 py-0.5 rounded font-semibold">
              {events.length}
            </span>
          </div>

          {events.length === 0 && !loading && (
            <p className="text-xs text-[#6e6459]">
              No events yet. Run a file through the pipeline from the Pipelines tab, or an evidence file has been
              parsed/extracted but not analyzed.
            </p>
          )}

          <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
            {events.map((evt) => {
              const isSelected = selectedEventId === evt.id;
              return (
                <motion.div
                  key={evt.id}
                  whileHover={{ scale: 1.02, y: -2 }}
                  transition={{ duration: 0.15 }}
                  onClick={() => setSelectedEventId(evt.id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer shadow-2xs hover:shadow-md ${
                    isSelected
                      ? 'border-[#1b4e39] bg-[#eaf1ed] shadow-xs ring-1 ring-[#1b4e39]/30'
                      : 'border-[#e4ded4] hover:border-[#1b4e39]/50 bg-[#fffdfa]'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-bold text-[#0f2338]">
                      {new Date(evt.start_time).toLocaleTimeString()}
                    </span>
                    <span className="text-[#2b4d3a] font-semibold">
                      {evt.confidence !== null ? `${(evt.confidence * 100).toFixed(0)}%` : '—'}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-[#221e1b] mt-1">
                    {evt.event_type} {evt.object_type ? `· ${evt.object_type}` : ''}
                  </div>
                  <div className="text-[10.5px] text-[#8c8275] font-mono mt-0.5">{evt.camera_id}</div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </motion.div>
  );
};