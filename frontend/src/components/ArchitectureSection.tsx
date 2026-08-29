import React, { useState } from 'react';
import { Fingerprint, Cpu, Activity, Copy, Check, Terminal, FileCode2, Sparkles, ShieldCheck, Scale, Database, Search, Video, ArrowDown } from 'lucide-react';
import { motion } from 'motion/react';
import { ArchitectureCardItem } from '../types';

const ARCHITECTURE_CARDS: ArchitectureCardItem[] = [
  {
    id: 'hashing',
    title: '1. Cryptographic Sealing (SHA-256)',
    description:
      'Preserving original bitstream integrity. Before demuxing or inference begins, raw evidence files are bit-copied and sealed using NIST FIPS 180-4 SHA-256 hashing to guarantee court admissibility.',
    iconType: 'fingerprint',
    iconColor: 'sage',
    codeLines: [
      { label: 'ALG', value: 'SHA-256 Bitstream' },
      { label: 'NIST', value: 'FIPS 180-4 Compliant' },
      { label: 'OUT', value: 'e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934e...' },
    ],
  },
  {
    id: 'parsing',
    title: '2. Deep Demuxing & Telemetry Extraction',
    description:
      'Extracting structured data and sensor streams. Video containers (MP4, MOV, AVI, MKV) are disassembled into raw video, synchronized audio, GPS coordinates, and camera EXIF telemetry.',
    iconType: 'parse',
    iconColor: 'sage',
    codeLines: [
      { label: 'FFPROBE', value: 'Stream #0:0(und) [Video]' },
      { label: 'CODEC', value: 'H.264 (High) (avc1) / ProRes' },
      { label: 'TELEMETRY', value: 'GPS: 37.7749° N, 122.4194° W' },
    ],
  },
  {
    id: 'analysis',
    title: '3. Neural Timeline & Forensic Analysis',
    description:
      'AI-driven timeline synthesis. High-precision neural models concurrently detect persons, track vehicles, transcribe audio dialogues, and flag critical anomalies into a searchable forensic index.',
    iconType: 'analysis',
    iconColor: 'sage',
    codeLines: [
      { label: 'MODEL', value: 'Multimodal Forensic Vision' },
      { label: 'EVENT', value: 'Person_Detected [Confidence: 94%]' },
      { label: 'TIMESTAMP', value: '00:14:22.050 (Frame #20,688)' },
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
      className={`w-full mt-14 sm:mt-18 pt-4 transition-all duration-700 rounded-3xl p-4 sm:p-6 ${
        isHighlighted 
          ? 'bg-[#eaf1ed]/50 ring-2 ring-[#1b4e39] shadow-[0_0_50px_rgba(27,78,57,0.15)]' 
          : ''
      }`}
    >
      {/* Section Header */}
      <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-12">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-[#1b4e39] uppercase tracking-[0.2em] font-['Manrope',sans-serif] bg-[#eaf1ed] border border-[#c9dcd0] px-3.5 py-1 rounded-full">
          <ShieldCheck className="w-3.5 h-3.5" />
          TraceX Architecture & Mission
        </span>
        <h2 className="text-[28px] sm:text-[36px] font-normal tracking-[-0.015em] text-[#221e1b] font-['EB_Garamond',serif] mt-3">
          What Does TraceX Do?
        </h2>
        <p className="text-[14px] sm:text-[15.5px] text-[#5c544c] mt-2.5 font-['Manrope',sans-serif] leading-relaxed">
          TraceX is an enterprise-grade digital forensic intelligence platform engineered to ingest, verify, analyze, and preserve video evidence with cryptographically unbreakable chain-of-custody standards.
        </p>
      </div>

      {/* Core Capabilities Executive Summary Banner */}
      <div className="bg-[#fcfbf8] border border-[#e6ded2] rounded-2xl p-6 sm:p-8 mb-8 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)]">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 divide-y md:divide-y-0 md:divide-x divide-[#ede5d8]">
          <div className="pr-0 md:pr-4 space-y-2">
            <div className="flex items-center gap-2 text-[#1b4e39] font-bold text-sm font-['Manrope']">
              <Scale className="w-4 h-4" />
              <span>Courtroom Admissibility</span>
            </div>
            <p className="text-xs text-[#6e6459] leading-relaxed">
              Every digital asset uploaded is bound to an immutable SHA-256 cryptographic hash compliant with ISO/IEC 27037 and FBI CJIS Level 4 policies.
            </p>
          </div>

          <div className="pt-4 md:pt-0 px-0 md:px-4 space-y-2">
            <div className="flex items-center gap-2 text-[#1b4e39] font-bold text-sm font-['Manrope']">
              <Sparkles className="w-4 h-4" />
              <span>AI Automated Chronology</span>
            </div>
            <p className="text-xs text-[#6e6459] leading-relaxed">
              Concurrently executes face recognition, object tracking, and speech-to-text to automatically generate frame-accurate event chronologies.
            </p>
          </div>

          <div className="pt-4 md:pt-0 pl-0 md:pl-4 space-y-2">
            <div className="flex items-center gap-2 text-[#1b4e39] font-bold text-sm font-['Manrope']">
              <Database className="w-4 h-4" />
              <span>Tamper-Evident Ledger</span>
            </div>
            <p className="text-xs text-[#6e6459] leading-relaxed">
              Maintains an immutable chain-of-custody ledger with operator attribution and exportable JSON audit packages for legal scrutiny.
            </p>
          </div>
        </div>
      </div>

      {/* 3 Architecture Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-7">
        {ARCHITECTURE_CARDS.map((card, idx) => {
          const isCopied = copiedCardId === card.id;

          return (
            <motion.div
              key={card.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.08 }}
              whileHover={{ y: -8, scale: 1.025 }}
              className="bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] p-6 sm:p-7 flex flex-col justify-between transition-all duration-300 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] hover:shadow-[0_20px_35px_-8px_rgba(34,30,27,0.12)] hover:border-[#1b4e39]/40 cursor-default group"
            >
              <div>
                {/* Top Icon Badge */}
                <div className="mb-5">
                  {card.iconType === 'fingerprint' && (
                    <div className="w-11 h-11 rounded-xl bg-[#eaf1ed] text-[#1b4e39] flex items-center justify-center shadow-xs border border-[#c9dcd0]">
                      <Fingerprint className="w-6 h-6 stroke-[1.8]" />
                    </div>
                  )}

                  {card.iconType === 'parse' && (
                    <div className="w-11 h-11 rounded-xl bg-[#eaf1ed] text-[#1b4e39] flex items-center justify-center shadow-xs border border-[#c9dcd0]">
                      <FileCode2 className="w-6 h-6 stroke-[1.8]" />
                    </div>
                  )}

                  {card.iconType === 'analysis' && (
                    <div className="w-11 h-11 rounded-xl bg-[#eaf1ed] text-[#1b4e39] flex items-center justify-center shadow-xs border border-[#c9dcd0]">
                      <Activity className="w-6 h-6 stroke-[1.8]" />
                    </div>
                  )}
                </div>

                {/* Card Title */}
                <h3 className="text-[19px] sm:text-[20px] font-semibold text-[#221e1b] font-['EB_Garamond',serif] tracking-tight">
                  {card.title}
                </h3>

                {/* Card Description */}
                <p className="text-[13px] sm:text-[13.5px] text-[#5c544c] mt-2 leading-relaxed font-['Manrope',sans-serif]">
                  {card.description}
                </p>
              </div>

              {/* Code / Terminal Snippet Box */}
              <div className="mt-6 pt-2">
                <div className="bg-[#f5efe4] rounded-xl p-3.5 border border-[#e4dcd0] font-['DM_Mono',monospace] text-[11.5px] text-[#2c2621] relative group">
                  <button
                    onClick={() => handleCopy(card)}
                    className="absolute top-2 right-2 p-1 rounded bg-white text-[#635b52] hover:text-[#221e1b] opacity-0 group-hover:opacity-100 transition-opacity border border-[#ded5c7] cursor-pointer"
                    title="Copy terminal snippet"
                  >
                    {isCopied ? <Check className="w-3 h-3 text-[#1b4e39]" /> : <Copy className="w-3 h-3" />}
                  </button>

                  <div className="space-y-1 select-all">
                    {card.codeLines.map((line, lineIdx) => (
                      <div key={lineIdx} className="leading-tight break-all">
                        <span className="font-bold text-[#221e1b]">{line.label}:</span>{' '}
                        <span className="text-[#5c544c]">{line.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
};

