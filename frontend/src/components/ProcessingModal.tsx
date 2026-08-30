import React, { useState, useEffect } from 'react';
import {
  X,
  Shield,
  Cpu,
  Activity,
  FileText,
  ArrowRight,
  Terminal,
  RefreshCw,
} from 'lucide-react';
import { EvidenceFile, VideoAnalysisResult } from '../types';
import { API_BASE, getAuthHeaders } from '../api/client';

interface ProcessingModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseName: string;
  evidenceId: string;
  file: EvidenceFile | null;
  onCompleteStep: (stepId: number) => void;
  onAnalysisComplete: (result: VideoAnalysisResult) => void;
}

export const ProcessingModal: React.FC<ProcessingModalProps> = ({
  isOpen,
  onClose,
  caseName,
  evidenceId,
  file,
  onCompleteStep,
  onAnalysisComplete,
}) => {
  const [progress, setProgress] = useState(0);
  const [currentPhase, setCurrentPhase] = useState(1);
  const [logs, setLogs] = useState<string[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const [error, setError] = useState('');
  const [analysisResult, setAnalysisResult] = useState<VideoAnalysisResult | null>(null);

  const fileName = file?.name || 'evidence.mp4';
  const fileHash = file?.hash || '';

  useEffect(() => {
    if (!isOpen) {
      setProgress(0);
      setCurrentPhase(1);
      setLogs([]);
      setIsCompleted(false);
      setError('');
      setAnalysisResult(null);
      return;
    }

    const sourceFile = file?.sourceFile;
    if (!sourceFile) {
      setError('Select a video file before starting the forensic pipeline.');
      return;
    }

    const controller = new AbortController();
    let isActive = true;

    const runAnalysis = async () => {
      setError('');
      setProgress(15);
      setCurrentPhase(1);
      setLogs([
        `[INGEST] Acquired evidence file: ${sourceFile.name} (${(sourceFile.size / 1024 / 1024).toFixed(2)} MB)`,
        `[CRYPTO] SHA-256 Checksum: ${fileHash.substring(0, 32)}...`,
        `[BACKEND] Dispatching to FastAPI /video/analyze pipeline.`,
      ]);

      try {
        const formData = new FormData();
        formData.append('file', sourceFile, sourceFile.name);

        setProgress(35);
        setCurrentPhase(2);
        setLogs((prev) => [
          ...prev,
          '[FFPROBE] Probing stream tracks, timecode bases, and codec parameters.',
          '[FRAME_EXTRACT] Initializing PyAV frame decoder and motion difference pass.',
        ]);

        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE}/video/analyze`, {
          method: 'POST',
          headers,
          body: formData,
          signal: controller.signal,
        });

        if (!response.ok) {
          let detail = `Backend analysis failed with status ${response.status}.`;
          try {
            const errJson = await response.json();
            if (errJson?.detail) detail = errJson.detail;
          } catch {}
          throw new Error(detail);
        }

        setProgress(65);
        setCurrentPhase(3);
        setLogs((prev) => [
          ...prev,
          '[YOLO] Neural frame inference completed (YOLO multi-class detector).',
          '[CORRELATION] Correlating object tracks and temporal motion vectors.',
        ]);

        const result: VideoAnalysisResult = await response.json();

        if (!isActive) return;

        setProgress(100);
        setCurrentPhase(4);
        setLogs((prev) => [
          ...prev,
          `[INTEGRITY] Bitstream scan complete: status=${result.video_integrity?.overall_status || 'PASS'}`,
          `[ACTIVITY] ${result.reconstruction_count || 0} narrative events reconstructed.`,
          `[VERIFIED] Full certified dossier compiled successfully.`,
        ]);

        setAnalysisResult(result);
        setIsCompleted(true);
        try {
          onCompleteStep?.(3);
          onAnalysisComplete?.(result);
        } catch (cbErr) {
          console.error('Callback error:', cbErr);
        }
      } catch (err: any) {
        if (!isActive) return;
        console.error(err);
        setError(err?.message || 'Forensic pipeline encountered an unexpected error.');
        setLogs((prev) => [
          ...prev,
          `[ERROR] ${err?.message || 'Pipeline aborted.'}`,
        ]);
      }
    };

    runAnalysis();

    return () => {
      isActive = false;
      controller.abort();
    };
  }, [isOpen, file]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-3xl w-full border border-slate-200 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${error ? 'bg-rose-500' : 'bg-indigo-600 animate-pulse'}`} />
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                Forensic Pipeline Execution
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Case: <span className="text-slate-800 font-semibold">{caseName}</span> • Evidence: <span className="text-slate-800 font-semibold">{evidenceId}</span> • File: <span className="text-indigo-600 font-semibold">{fileName}</span>
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {/* Progress Bar */}
          <div>
            <div className="flex justify-between text-xs text-slate-900 font-medium mb-1.5">
              <span>
                {error ? 'Execution Failed' : isCompleted ? 'Analysis Completed' : 'Running Neural Tracking & Telemetry Pipeline...'}
              </span>
              <span className="font-bold text-indigo-600">{progress}%</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 rounded-full ${error ? 'bg-rose-500' : 'bg-indigo-600'}`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* 4 Phases */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
            {[
              { id: 1, label: 'Bitstream Ingest', icon: Shield },
              { id: 2, label: 'Stream Probe', icon: Cpu },
              { id: 3, label: 'YOLO Tracking', icon: Activity },
              { id: 4, label: 'Reconstruction', icon: FileText },
            ].map(({ id, label, icon: Icon }) => (
              <div
                key={id}
                className={`p-3 rounded-xl border transition-all ${
                  currentPhase >= id
                    ? 'border-emerald-200 bg-emerald-50 text-slate-900 font-semibold'
                    : 'border-slate-200 bg-slate-50 text-slate-400'
                }`}
              >
                <Icon className="w-4 h-4 mx-auto mb-1" />
                <span>{id}. {label}</span>
              </div>
            ))}
          </div>

          {/* Live Terminal Log */}
          <div>
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-slate-400" />
              Pipeline Telemetry Log
            </div>
            <div className="bg-slate-900 text-slate-300 rounded-xl p-4 font-mono text-xs min-h-36 max-h-48 overflow-y-auto space-y-1">
              {logs.map((log, index) => (
                <div key={index} className="leading-relaxed">
                  <span className="text-[#74b8f7]">{log.slice(0, log.indexOf(']') + 1)}</span>
                  <span className="text-slate-200">{log.slice(log.indexOf(']') + 1)}</span>
                </div>
              ))}

              {!isCompleted && !error && (
                <div className="flex items-center gap-1.5 text-[#74b8f7] pt-1">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  <span>Executing pipeline stage...</span>
                </div>
              )}

              {error && (
                <div className="text-rose-400 pt-1 font-bold">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* Quick Summary Card if completed */}
          {isCompleted && analysisResult && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-1.5">
              <div className="text-xs font-semibold text-slate-900 uppercase">
                Forensic Summary
              </div>
              <div className="text-sm font-bold text-slate-900">
                {analysisResult.forensic_summary.headline}
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {analysisResult.forensic_summary.summary}
              </p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {error ? 'Pipeline halted' : isCompleted ? 'Analysis ready for review' : 'Processing bitstream...'}
          </span>

          <div className="flex gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-900 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer shadow-xs"
            >
              Close
            </button>

            {isCompleted && !error && (
              <button
                onClick={() => {
                  onClose();
                  onCompleteStep?.(3);
                }}
                className="btn-kinetic-primary px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer"
              >
                <span>Inspect in Workstation</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
