import React from 'react';
import { X, Shield, Cpu, Activity, FileText, ArrowRight, AlertTriangle } from 'lucide-react';

export interface PipelineState {
  phase: 1 | 2 | 3 | 4; // 1 upload/hash, 2 parse, 3 extract, 4 analyze
  progress: number; // 0-100
  logs: string[];
  isCompleted: boolean;
  error: string | null;
}

interface ProcessingModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseName: string;
  fileName: string;
  state: PipelineState;
  onReviewTimeline: () => void;
}

export const ProcessingModal: React.FC<ProcessingModalProps> = ({
  isOpen,
  onClose,
  caseName,
  fileName,
  state,
  onReviewTimeline,
}) => {
  if (!isOpen) return null;

  const { phase, progress, logs, isCompleted, error } = state;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1e1b18]/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#fcfbf8] rounded-2xl max-w-2xl w-full border border-[#e6ded2] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="px-6 py-5 border-b border-[#e6ded2] flex items-center justify-between bg-[#f5efe4]">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`inline-block w-2.5 h-2.5 rounded-full ${
                  error ? 'bg-[#c2593f]' : 'bg-[#3b5749] animate-pulse'
                }`}
              />
              <h3 className="text-[18px] font-semibold text-[#221e1b] font-['DM_Sans',sans-serif]">
                Forensic Pipeline Execution
              </h3>
            </div>
            <p className="text-xs text-[#6e6459] font-mono mt-0.5">
              Case: <span className="font-semibold text-[#221e1b]">{caseName}</span> • File:{' '}
              <span className="font-semibold text-[#221e1b]">{fileName}</span>
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 text-[#8c8275] hover:text-[#221e1b] rounded-lg hover:bg-black/5 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <div className="flex justify-between text-xs font-medium text-[#221e1b] mb-2 font-mono">
              <span className="font-semibold">
                {error ? 'Pipeline failed' : isCompleted ? 'Analysis Completed' : 'Running evidence pipeline…'}
              </span>
              <span className="font-bold text-[#0f2338]">{progress}%</span>
            </div>
            <div className="w-full h-2.5 bg-[#e8dfd2] rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 rounded-full ${error ? 'bg-[#c2593f]' : 'bg-[#0f2338]'}`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
            {[
              { id: 1, label: 'Upload & Hash', icon: Shield },
              { id: 2, label: 'Parse', icon: Cpu },
              { id: 3, label: 'Extract', icon: Activity },
              { id: 4, label: 'Analyze', icon: FileText },
            ].map(({ id, label, icon: Icon }) => (
              <div
                key={id}
                className={`p-2.5 rounded-xl border transition-all ${
                  phase >= id
                    ? 'border-[#3b5749] bg-[#eaf1ed] text-[#2b4d3a] font-bold'
                    : 'border-[#e6ded2] text-[#8c8275]'
                }`}
              >
                <Icon className="w-4 h-4 mx-auto mb-1 text-[#3b5749]" />
                <span>
                  {id}. {label}
                </span>
              </div>
            ))}
          </div>

          <div>
            <div className="text-[11px] font-bold text-[#6e6459] uppercase tracking-wider mb-1.5 font-mono">
              Pipeline Log
            </div>
            <div className="bg-[#141b22] text-[#c9dcd0] rounded-xl p-3.5 font-mono text-[11.5px] h-36 overflow-y-auto space-y-1 scrollbar-thin border border-[#232f3d]">
              {logs.map((log, index) => (
                <div key={index} className="leading-relaxed">
                  {log}
                </div>
              ))}
              {!isCompleted && !error && (
                <div className="flex items-center gap-1.5 text-[#eaf1ed]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#5e7d6f] animate-ping" />
                  <span>Waiting on backend…</span>
                </div>
              )}
              {error && (
                <div className="flex items-start gap-1.5 text-[#e2937c]">
                  <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-[#f5efe4] border-t border-[#e6ded2] flex items-center justify-between">
          <span className="text-xs font-mono text-[#6e6459]">
            {error ? 'Check the log above' : isCompleted ? '✓ Evidence processed' : 'Do not close this tab'}
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-[#5c544c] bg-white border border-[#ded5c7] rounded-lg hover:bg-black/5 transition-colors cursor-pointer"
            >
              Close
            </button>
            {isCompleted && !error && (
              <button
                onClick={onReviewTimeline}
                className="btn-primary-navy px-4 py-2 text-xs font-semibold text-white rounded-lg flex items-center gap-1.5 cursor-pointer"
              >
                <span>Review Generated Timeline</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};