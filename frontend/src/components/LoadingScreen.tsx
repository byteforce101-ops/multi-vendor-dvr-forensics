import React, { useState, useEffect } from 'react';
import { ShieldCheck, CheckCircle2, Cpu, HardDrive } from 'lucide-react';
import TraceXLogo from './TraceXLogo';

export interface LoadingScreenProps {
  isVisible: boolean;
  variant?: 'simple' | 'detailed';
  title?: string;
  subtitle?: string;
  steps?: string[];
  durationMs?: number;
  onComplete?: () => void;
}

export const LoadingScreen: React.FC<LoadingScreenProps> = ({
  isVisible,
  variant = 'simple',
  title = 'Loading...',
  subtitle = 'Please wait while workspace updates',
  steps = [],
  durationMs = 1800,
  onComplete,
}) => {
  const [progress, setProgress] = useState(0);
  const [currentStepIdx, setCurrentStepIdx] = useState(0);

  useEffect(() => {
    if (!isVisible) {
      setProgress(0);
      setCurrentStepIdx(0);
      return;
    }

    setProgress(0);
    setCurrentStepIdx(0);

    const stepCount = steps.length || 1;
    const intervalTime = 30;
    const totalSteps = durationMs / intervalTime;
    const increment = 100 / totalSteps;

    let currentProgress = 0;

    const timer = setInterval(() => {
      currentProgress += increment;

      if (currentProgress >= 100) {
        currentProgress = 100;
        setProgress(100);
        setCurrentStepIdx(stepCount - 1);
        clearInterval(timer);

        setTimeout(() => {
          if (onComplete) {
            onComplete();
          }
        }, 80);
      } else {
        setProgress(Math.min(99, Math.round(currentProgress)));
        const calculatedStep = Math.min(
          stepCount - 1,
          Math.floor((currentProgress / 100) * stepCount)
        );
        setCurrentStepIdx(calculatedStep);
      }
    }, intervalTime);

    return () => {
      clearInterval(timer);
    };
  }, [isVisible, title, durationMs, steps]);

  if (!isVisible) return null;

  // -------------------------------------------------------------------------
  // 1. SIMPLE BASIC LOADER (Logo + Name + Spinner - Used Everywhere Else)
  // -------------------------------------------------------------------------
  if (variant === 'simple') {
    return (
      <div className="fixed inset-0 z-[99999] flex flex-col items-center justify-center bg-[#f5f6f7] text-[#172554] select-none">
        <div className="flex flex-col items-center justify-center p-6 text-center">
          <TraceXLogo variant="dark" className="h-11 w-auto object-contain mb-4 animate-pulse" />
          <h2 className="text-sm font-bold text-slate-800 tracking-tight mb-1">
            {title || 'TraceX — DVR Forensics'}
          </h2>
          <div className="flex items-center gap-2.5 mt-3 text-xs font-medium text-slate-600 bg-white px-4 py-2 rounded-full border border-slate-200 shadow-xs">
            <div className="w-4 h-4 border-2 border-[#172554] border-t-transparent rounded-full animate-spin" />
            <span>{subtitle || 'Loading workspace...'}</span>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // 2. DETAILED PIPELINE LOADER (Used ONLY after File Upload before Pipeline)
  // -------------------------------------------------------------------------
  return (
    <div
      className="fixed inset-0 z-[99999] flex flex-col items-center justify-center bg-[#070a11] text-slate-100 select-none overflow-hidden"
      style={{
        backgroundImage:
          'radial-gradient(circle at 50% 40%, rgba(30, 58, 138, 0.18) 0%, rgba(7, 10, 17, 0.95) 75%)',
      }}
    >
      {/* Background Matrix / Grid overlay */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(#38bdf8 1px, transparent 1px), linear-gradient(90deg, #38bdf8 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-[min(540px,92vw)] p-8 rounded-2xl bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 shadow-2xl flex flex-col items-center text-center">
        {/* Top Status Ticker Badge */}
        <div className="flex items-center justify-between w-full pb-6 mb-6 border-b border-slate-800/80 text-[10px] font-mono tracking-wider text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-400 font-semibold uppercase">TRACEX CORE ENGINE</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>AES-256 SECURED</span>
          </div>
        </div>

        {/* Brand Logo */}
        <div className="relative mb-6 flex items-center justify-center">
          <div className="absolute -inset-4 bg-cyan-500/10 rounded-full blur-xl animate-pulse" />
          <TraceXLogo variant="white" className="h-10 w-auto object-contain relative z-10" />
        </div>

        {/* Title */}
        <h2 className="text-lg font-bold text-white tracking-tight mb-1">
          {title}
        </h2>
        <p className="text-xs text-slate-400 mb-6 max-w-sm leading-relaxed">
          {subtitle}
        </p>

        {/* Dynamic Micro-Step Terminal Ticker */}
        <div className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl p-3.5 mb-6 text-left font-mono text-[11px] space-y-2 shadow-inner">
          {steps.map((stepText, idx) => {
            const isDone = idx < currentStepIdx;
            const isCurrent = idx === currentStepIdx;

            return (
              <div
                key={idx}
                className={`flex items-center justify-between transition-all duration-300 ${
                  isDone
                    ? 'text-emerald-400'
                    : isCurrent
                    ? 'text-cyan-300 font-semibold'
                    : 'text-slate-600 opacity-60'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  {isDone ? (
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                  ) : isCurrent ? (
                    <span className="w-3.5 h-3.5 shrink-0 flex items-center justify-center">
                      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                    </span>
                  ) : (
                    <span className="w-3.5 h-3.5 shrink-0 flex items-center justify-center text-[10px]">
                      ○
                    </span>
                  )}
                  <span className="truncate">{stepText}</span>
                </div>
                {isDone && <span className="text-[9px] uppercase font-bold text-emerald-500/80">DONE</span>}
                {isCurrent && <span className="text-[9px] uppercase font-bold text-cyan-400 animate-pulse">PROC</span>}
              </div>
            );
          })}
        </div>

        {/* Progress Bar */}
        <div className="w-full space-y-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400 text-[10px] tracking-wider uppercase">Processing Payload</span>
            <span className="text-cyan-400 font-bold">{progress}%</span>
          </div>

          <div className="w-full h-2.5 bg-slate-950 rounded-full p-0.5 border border-slate-800 overflow-hidden relative">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-600 via-cyan-500 to-teal-400 transition-all duration-75 ease-out relative shadow-[0_0_12px_rgba(6,182,212,0.6)]"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute top-0 right-0 bottom-0 w-3 bg-white/40 blur-[1px] animate-pulse rounded-full" />
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-6 pt-4 border-t border-slate-800/60 w-full flex items-center justify-between text-[10px] font-mono text-slate-500">
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3 h-3 text-slate-400" />
            <span>NEURAL VISION THREAD #01</span>
          </div>
          <div className="flex items-center gap-1.5">
            <HardDrive className="w-3 h-3 text-slate-400" />
            <span>BUFFER: READY</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoadingScreen;
