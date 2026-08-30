import React from 'react';
import { Check, Shield, Cpu, Activity, FileCheck2 } from 'lucide-react';
import { motion } from 'motion/react';

interface ProcessPipelineProps {
  currentStepId: number; // 1 Intake, 2 Extraction, 3 AI Analytics, 4 Review
}

const STEPS = [
  { id: 1, label: '1. Ingest & Hash', icon: Shield },
  { id: 2, label: '2. Stream Carving', icon: Cpu },
  { id: 3, label: '3. CV & Integrity', icon: Activity },
  { id: 4, label: '4. Case Dossier', icon: FileCheck2 },
];

export const ProcessPipeline: React.FC<ProcessPipelineProps> = ({ currentStepId }) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="w-full bg-[#08101E] rounded-lg border border-[#1E3A5F] p-4 sm:p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#00D2FF] animate-pulse" />
          <h2 className="text-[13px] font-bold tracking-wider text-slate-100 uppercase font-mono">
            // FORENSIC EVIDENCE PIPELINE
          </h2>
        </div>
        <span className="text-[11px] font-mono text-[#00D2FF] bg-[#0284C7]/15 border border-[#0284C7]/30 px-2 py-0.5 rounded font-semibold">
          STAGE {Math.min(currentStepId, STEPS.length)} OF {STEPS.length}
        </span>
      </div>

      <div className="relative px-2">
        <div className="absolute top-[14px] left-[24px] right-[24px] h-[2px] bg-[#142842]" aria-hidden="true" />
        <div
          className="absolute top-[14px] left-[24px] h-[2px] bg-[#00D2FF] transition-all duration-300 shadow-[0_0_8px_#00D2FF]"
          style={{ width: `${((Math.min(currentStepId, STEPS.length) - 1) / (STEPS.length - 1)) * 100}%`, maxWidth: 'calc(100% - 48px)' }}
          aria-hidden="true"
        />

        <div className="relative flex items-start justify-between">
          {STEPS.map((step) => {
            const isCompleted = step.id < currentStepId;
            const isActive = step.id === currentStepId;
            const Icon = step.icon;

            return (
              <div key={step.id} className="flex flex-col items-center gap-1.5" style={{ width: `${100 / STEPS.length}%` }}>
                {isCompleted ? (
                  <div className="w-[28px] h-[28px] rounded bg-[#10B981] text-black flex items-center justify-center shadow-[0_0_10px_rgba(16,185,129,0.3)]">
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  </div>
                ) : isActive ? (
                  <div className="w-[28px] h-[28px] rounded bg-[#0D192E] border-2 border-[#00D2FF] text-[#00D2FF] flex items-center justify-center shadow-[0_0_12px_rgba(0,210,255,0.4)]">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                ) : (
                  <div className="w-[28px] h-[28px] rounded bg-[#0D192E] border border-[#1E3A5F] text-[#64748B] flex items-center justify-center text-[10px] font-mono font-bold">
                    {step.id}
                  </div>
                )}
                <span className={`text-[11px] font-mono ${isActive ? 'font-bold text-[#00D2FF]' : isCompleted ? 'font-semibold text-slate-300' : 'text-[#64748B]'}`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </motion.section>
  );
};