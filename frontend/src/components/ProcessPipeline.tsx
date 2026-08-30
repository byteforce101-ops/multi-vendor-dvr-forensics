import React from 'react';
import { Check } from 'lucide-react';
import { motion } from 'motion/react';

interface ProcessPipelineProps {
  currentStepId: number; // 1 Sign in, 2 Upload, 3 Analyze, 4 Review
}

const STEPS = [
  { id: 1, label: 'Sign in' },
  { id: 2, label: 'Upload' },
  { id: 3, label: 'Analyze' },
  { id: 4, label: 'Review' },
];

export const ProcessPipeline: React.FC<ProcessPipelineProps> = ({ currentStepId }) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] p-6 sm:p-7"
    >
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-[22px] font-normal tracking-[-0.015em] text-[#221e1b] font-['DM_Sans',sans-serif]">
          Evidence Workflow
        </h1>
        <span className="text-[11px] font-mono text-[#8c8275]">
          Step {Math.min(currentStepId, STEPS.length)} of {STEPS.length}
        </span>
      </div>

      <div className="relative px-2">
        <div className="absolute top-[15px] left-[24px] right-[24px] h-px bg-[#e3dad0]" aria-hidden="true" />
        <div
          className="absolute top-[15px] left-[24px] h-px bg-[#1b4e39] transition-all duration-400"
          style={{ width: `${((Math.min(currentStepId, STEPS.length) - 1) / (STEPS.length - 1)) * 100}%`, maxWidth: 'calc(100% - 48px)' }}
          aria-hidden="true"
        />

        <div className="relative flex items-start justify-between">
          {STEPS.map((step) => {
            const isCompleted = step.id < currentStepId;
            const isActive = step.id === currentStepId;
            return (
              <div key={step.id} className="flex flex-col items-center gap-2" style={{ width: `${100 / STEPS.length}%` }}>
                {isCompleted ? (
                  <div className="w-[30px] h-[30px] rounded-full bg-[#1b4e39] text-white flex items-center justify-center">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                ) : isActive ? (
                  <div className="w-[30px] h-[30px] rounded-full bg-[#fcfbf8] border-2 border-[#1b4e39] flex items-center justify-center">
                    <div className="w-[10px] h-[10px] rounded-full bg-[#1b4e39]" />
                  </div>
                ) : (
                  <div className="w-[30px] h-[30px] rounded-full border border-[#d6cbbe] text-[#8c8275] flex items-center justify-center text-[11px] font-semibold">
                    {step.id}
                  </div>
                )}
                <span className={`text-[12px] ${isActive ? 'font-bold text-[#1b4e39]' : isCompleted ? 'font-semibold text-[#221e1b]' : 'text-[#8c8275]'}`}>
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