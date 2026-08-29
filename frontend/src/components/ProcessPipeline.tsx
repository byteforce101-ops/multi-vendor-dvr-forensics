import React from 'react';
import { Check } from 'lucide-react';
import { motion } from 'motion/react';
import { PipelineStep } from '../types';

interface ProcessPipelineProps {
  currentStepId: number;
  onSelectStep?: (stepId: number) => void;
}

const DEFAULT_STEPS: PipelineStep[] = [
  { id: 1, label: 'Sign In', status: 'completed', description: 'Enterprise identity verified' },
  { id: 2, label: 'Create Case', status: 'completed', description: 'Case dossier registered' },
  { id: 3, label: 'Upload Evidence', status: 'active', description: 'Raw video bitstream ingestion' },
  { id: 4, label: 'Hash', status: 'pending', description: 'SHA-256 cryptographic bit-seal' },
  { id: 5, label: 'Parse', status: 'pending', description: 'FFmpeg demuxing & metadata dissection' },
  { id: 6, label: 'Extract Recordings', status: 'pending', description: 'Telemetry & audio isolation' },
  { id: 7, label: 'Analyze', status: 'pending', description: 'Object, facial, and audio transcription' },
  { id: 8, label: 'Review Timeline', status: 'pending', description: 'Synchronized event verification' },
  { id: 9, label: 'Export Report', status: 'pending', description: 'CJIS certified forensic dossier' },
];

export const ProcessPipeline: React.FC<ProcessPipelineProps> = ({
  currentStepId = 3,
  onSelectStep,
}) => {
  return (
    <motion.section 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] p-6 sm:p-8 lg:p-9"
    >
      {/* Title & Subtitle */}
      <div className="mb-7 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[#eee7db] pb-4">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-normal tracking-[-0.015em] text-[#221e1b] font-['EB_Garamond',serif]">
            Process Pipeline
          </h1>
          <p className="text-[13.5px] sm:text-[14px] text-[#5c544c] mt-1 font-['Manrope',sans-serif] font-normal">
            Ensure evidentiary integrity by following the verified path. Your current progress is highlighted below.
          </p>
        </div>

        <span className="text-[11.5px] font-mono text-[#3b5749] bg-[#eaf1ed] border border-[#c9dcd0] px-3 py-1 rounded-md self-start sm:self-auto font-semibold">
          STEP {currentStepId} OF 9 ACTIVE
        </span>
      </div>

      {/* Stepper Bar Container */}
      <div className="overflow-x-auto pb-2 scrollbar-none">
        <div className="min-w-[760px] relative px-3">
          {/* Background Connecting Line */}
          <div 
            className="absolute top-[17px] left-[32px] right-[32px] h-[2px] bg-[#e3dad0] z-0" 
            aria-hidden="true"
          />

          {/* Active progress connecting line up to current step */}
          <div 
            className="absolute top-[17px] left-[32px] h-[2px] bg-[#1b4e39] z-0 transition-all duration-400"
            style={{
              width: `${((Math.min(currentStepId, 9) - 1) / 8) * 100}%`,
              maxWidth: 'calc(100% - 64px)'
            }}
            aria-hidden="true"
          />

          {/* Stepper Nodes */}
          <div className="relative z-10 flex items-start justify-between">
            {DEFAULT_STEPS.map((step) => {
              const isCompleted = step.id < currentStepId;
              const isActive = step.id === currentStepId;
              const isPending = step.id > currentStepId;

              return (
                <div
                  key={step.id}
                  onClick={() => onSelectStep && onSelectStep(step.id)}
                  className="flex flex-col items-center group cursor-pointer"
                  style={{ width: `${100 / DEFAULT_STEPS.length}%` }}
                >
                  {/* Circle Node */}
                  <div className="relative flex items-center justify-center">
                    {isCompleted && (
                      <div className="w-[34px] h-[34px] rounded-full bg-[#1b4e39] text-white flex items-center justify-center shadow-xs transition-transform group-hover:scale-110">
                        <Check className="w-4 h-4 stroke-[2.6]" />
                      </div>
                    )}

                    {isActive && (
                      <div className="w-[34px] h-[34px] rounded-full bg-[#fcfbf8] border-[2.5px] border-[#1b4e39] flex items-center justify-center shadow-md shadow-[#1b4e39]/20 transition-transform group-hover:scale-110">
                        <div className="w-[12px] h-[12px] rounded-full bg-[#1b4e39]"></div>
                      </div>
                    )}

                    {isPending && (
                      <div className="w-[34px] h-[34px] rounded-full bg-[#fcfbf8] border border-[#d6cbbe] text-[#8c8275] flex items-center justify-center text-[12px] font-semibold transition-colors group-hover:border-[#1b4e39] group-hover:text-[#1b4e39]">
                        {step.id}
                      </div>
                    )}
                  </div>

                  {/* Label */}
                  <span
                    className={`mt-2.5 text-[12px] sm:text-[12.5px] text-center whitespace-nowrap transition-colors ${
                      isActive
                        ? 'font-bold text-[#1b4e39]'
                        : isCompleted
                        ? 'font-semibold text-[#221e1b]'
                        : 'font-medium text-[#7d7367] group-hover:text-[#221e1b]'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </motion.section>
  );
};
