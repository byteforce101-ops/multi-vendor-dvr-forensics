import React, { useState } from 'react';
import { Fingerprint, Cpu, Activity, Copy, Check, Terminal, FileCode2, Sparkles, ShieldCheck, Scale, Database, Search, Video, ArrowDown } from 'lucide-react';
import { motion } from 'motion/react';
import { ArchitectureCardItem } from '../types';

const ARCHITECTURE_CARDS: ArchitectureCardItem[] = [
  {
    id: 'hashing',
    title: '1. Bitstream Ingest & WORM Seal',
    description:
      'NIST FIPS 180-4 SHA-256 and MD5 cryptographic hashing directly upon physical or virtual stream acquisition.',
    iconType: 'fingerprint',
    iconColor: 'cyan',
    codeLines: [
      { label: 'ALGORITHM', value: 'SHA-256 / MD5 Dual Pass' },
      { label: 'STANDARD', value: 'NIST SP 800-86 / ISO 27037' },
      { label: 'BITSTREAM', value: 'Mode 0444 Immutable WORM Storage' },
    ],
  },
  {
    id: 'parsing',
    title: '2. Low-Level Stream Carving & Demux',
    description:
      'Deep frame-by-frame PyAV dissection parsing raw PTS/DTS timecodes, keyframe GOP cadences, and codec syntax.',
    iconType: 'parse',
    iconColor: 'cyan',
    codeLines: [
      { label: 'PARSER', value: 'PyAV Native C-Bindings (FFmpeg 7.0)' },
      { label: 'DEMUX', value: 'H.264 (AVC) / H.265 (HEVC) / MP4 / MKV' },
      { label: 'INTEGRITY', value: 'Delta PTS Scan & FPS Variance Monitor' },
    ],
  },
  {
    id: 'analysis',
    title: '3. CV Inference & Timeline Correlation',
    description:
      'OpenCV multi-stage forensic vision tracking (HOG, Haar Cascades, MOG2) with kinematics and heuristic behavioral reconstruction.',
    iconType: 'analysis',
    iconColor: 'cyan',
    codeLines: [
      { label: 'INFERENCE', value: 'OpenCV HOG + Haar + MOG2 Kinematics' },
      { label: 'DETECTION', value: 'Persons, Vehicles, Motion Flux, Loss' },
      { label: 'DOSSIER', value: 'Certified JSON Chronological Timeline' },
    ],
  },
];

interface ArchitectureSectionProps {
  isHighlighted?: boolean;
}

export const ArchitectureSection: React.FC<ArchitectureSectionProps> = ({ isHighlighted = false }) => {
  const [copiedCardId, setCopiedCardId] = useState<string | null>(null);

  const handleCopy = (card: ArchitectureCardItem) => {
    const text = card.codeLines.map((l) => `${l.label}: ${l.value}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopiedCardId(card.id);
    setTimeout(() => setCopiedCardId(null), 2000);
  };

  return (
    <section 
      id="architecture-overview" 
      className={`w-full mt-10 pt-4 transition-all duration-500 rounded-lg p-5 border ${
        isHighlighted 
          ? 'bg-[#0D192E] border-[#00D2FF] shadow-[0_0_30px_rgba(0,210,255,0.2)]' 
          : 'bg-[#08101E] border-[#1E3A5F]'
      }`}
    >
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#1E3A5F] gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00D2FF]" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
              // FORENSIC ENGINE SYSTEM ARCHITECTURE & DATA PIPELINE
            </h3>
          </div>
          <p className="text-xs text-[#94A3B8] font-mono mt-0.5">
            Courtroom-admissible video ingestion, stream integrity validation, and neural activity reconstruction
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-[#00D2FF]">
          <span className="px-2 py-0.5 bg-[#0284C7]/20 border border-[#0284C7]/40 rounded font-bold">
            FASTAPI + PYAV + OPENCV FORENSICS
          </span>
        </div>
      </div>

      {/* 3 Architecture Specs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
        {ARCHITECTURE_CARDS.map((card) => {
          const isCopied = copiedCardId === card.id;

          return (
            <div
              key={card.id}
              className="bg-[#0D192E] rounded border border-[#1E3A5F] p-4 flex flex-col justify-between hover:border-[#00D2FF]/50 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-8 h-8 rounded bg-[#0284C7]/20 border border-[#0284C7]/40 text-[#00D2FF] flex items-center justify-center">
                    {card.iconType === 'fingerprint' && <Fingerprint className="w-4 h-4" />}
                    {card.iconType === 'parse' && <FileCode2 className="w-4 h-4" />}
                    {card.iconType === 'analysis' && <Activity className="w-4 h-4" />}
                  </div>
                  <span className="text-[10px] font-mono text-[#64748B] uppercase">MODULE {card.id.toUpperCase()}</span>
                </div>

                <h4 className="text-xs font-bold text-slate-100 font-mono tracking-tight">
                  {card.title}
                </h4>

                <p className="text-xs text-[#94A3B8] mt-1.5 leading-relaxed font-mono">
                  {card.description}
                </p>
              </div>

              {/* Code / Terminal Snippet Box */}
              <div className="mt-4 pt-2 border-t border-[#1E3A5F]">
                <div className="bg-[#040812] rounded p-2.5 border border-[#142842] font-mono text-[10.5px] text-slate-300 relative group">
                  <button
                    onClick={() => handleCopy(card)}
                    className="absolute top-1.5 right-1.5 p-1 rounded bg-[#0D192E] text-slate-400 hover:text-[#00D2FF] border border-[#1E3A5F] cursor-pointer"
                    title="Copy specification"
                  >
                    {isCopied ? <Check className="w-3 h-3 text-[#10B981]" /> : <Copy className="w-3 h-3" />}
                  </button>

                  <div className="space-y-1 select-all pr-6">
                    {card.codeLines.map((line, lineIdx) => (
                      <div key={lineIdx} className="leading-tight break-all">
                        <span className="font-bold text-[#00D2FF]">{line.label}:</span>{' '}
                        <span className="text-slate-300">{line.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};


