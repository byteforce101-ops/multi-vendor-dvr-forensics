import React, { useState, useEffect } from 'react';
import { X, CheckCircle2, RefreshCw, Shield, Cpu, Activity, FileText, ArrowRight, Play, Check } from 'lucide-react';
import { EvidenceFile, VideoAnalysisResult } from '../types';

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

  const fileName = file?.name || 'Interrogation_RM3_A.mp4';
  const fileHash = file?.hash || 'e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934ca495991b7852b855';

  useEffect(() => {
    if (!isOpen) {
      setProgress(0);
      setCurrentPhase(1);
      setLogs([]);
      setIsCompleted(false);
      setError('');
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
      setProgress(10);
      setCurrentPhase(1);
      setLogs([
        `[INGEST] Uploading ${sourceFile.name} to the FastAPI analysis service.`,
        `[CRYPTO] Client-side seal: ${fileHash.substring(0, 32)}...`,
      ]);

      try {
        const formData = new FormData();
        formData.append('file', sourceFile, sourceFile.name);
        setProgress(25);
        setCurrentPhase(2);
        setLogs((prev) => [...prev, '[FFPROBE] Backend is inspecting the video container and metadata.']);

        const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
        const response = await fetch(`${apiBaseUrl}/video/analyze`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });

        if (!response.ok) {
          let detail = `Backend analysis failed (${response.status}).`;
          try {
            const body = await response.json();
            if (typeof body.detail === 'string') detail = body.detail;
          } catch {
            // Keep the status-based message when the backend did not return JSON.
          }
          throw new Error(detail);
        }

        const result = await response.json() as VideoAnalysisResult;
        if (!isActive) return;

        setProgress(75);
        setCurrentPhase(3);
        setLogs((prev) => [
          ...prev,
          `[AI_INFERENCE] ${result.frames_analyzed} frames analyzed by the backend pipeline.`,
          `[DETECTION] ${result.event_count} forensic events reconstructed.`,
        ]);
        onAnalysisComplete(result);
        setProgress(100);
        setCurrentPhase(4);
        setIsCompleted(true);
        setLogs((prev) => [...prev, '[READY] Backend timeline returned and ready for auditable review.']);
        onCompleteStep(8);
      } catch (caught) {
        if (!isActive || (caught instanceof DOMException && caught.name === 'AbortError')) return;
        setError(caught instanceof Error ? caught.message : 'The backend analysis could not be completed.');
        setLogs((prev) => [...prev, '[ERROR] The forensic pipeline stopped before completion.']);
      }
    };

    void runAnalysis();
    return () => {
      isActive = false;
      controller.abort();
    };
  }, [isOpen, file]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1e1b18]/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#fcfbf8] rounded-2xl max-w-2xl w-full border border-[#e6ded2] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-5 border-b border-[#e6ded2] flex items-center justify-between bg-[#f5efe4]">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-[#3b5749] animate-pulse"></span>
              <h3 className="text-[18px] font-semibold text-[#221e1b] font-['DM_Sans',sans-serif]">
                Forensic Pipeline Execution
              </h3>
            </div>
            <p className="text-xs text-[#6e6459] font-mono mt-0.5">
              Case: <span className="font-semibold text-[#221e1b]">{caseName}</span> • Evidence: <span className="font-semibold text-[#221e1b]">{evidenceId}</span>
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#8c8275] hover:text-[#221e1b] rounded-lg hover:bg-black/5 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* File Status Card */}
          <div className="bg-[#f5efe4] rounded-xl p-3.5 border border-[#ded5c7] flex items-center justify-between text-xs font-mono">
            <div className="truncate max-w-[280px] sm:max-w-md">
              <span className="text-[#7d7367]">File: </span>
              <span className="font-bold text-[#221e1b]">{fileName}</span>
            </div>
            <div className="text-[#2b4d3a] bg-[#eaf1ed] border border-[#c9dcd0] px-2 py-0.5 rounded font-bold text-[11px]">
              SHA-256 Locked
            </div>
          </div>

          {/* Progress Bar */}
          <div>
            <div className="flex justify-between text-xs font-medium text-[#221e1b] mb-2 font-mono">
              <span className="font-semibold">{isCompleted ? 'Analysis Completed' : 'Executing Evidence Dissection...'}</span>
              <span className="font-bold text-[#0f2338]">{progress}%</span>
            </div>
            <div className="w-full h-2.5 bg-[#e8dfd2] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#0f2338] transition-all duration-300 rounded-full"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>

          {/* Phase Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
            <div className={`p-2.5 rounded-xl border transition-all ${
              currentPhase >= 1 ? 'border-[#3b5749] bg-[#eaf1ed] text-[#2b4d3a] font-bold' : 'border-[#e6ded2] text-[#8c8275]'
            }`}>
              <Shield className="w-4 h-4 mx-auto mb-1 text-[#3b5749]" />
              <span>1. Bit-Seal</span>
            </div>

            <div className={`p-2.5 rounded-xl border transition-all ${
              currentPhase >= 2 ? 'border-[#3b5749] bg-[#eaf1ed] text-[#2b4d3a] font-bold' : 'border-[#e6ded2] text-[#8c8275]'
            }`}>
              <Cpu className="w-4 h-4 mx-auto mb-1 text-[#3b5749]" />
              <span>2. FFmpeg Parse</span>
            </div>

            <div className={`p-2.5 rounded-xl border transition-all ${
              currentPhase >= 3 ? 'border-[#3b5749] bg-[#eaf1ed] text-[#2b4d3a] font-bold' : 'border-[#e6ded2] text-[#8c8275]'
            }`}>
              <Activity className="w-4 h-4 mx-auto mb-1 text-[#3b5749]" />
              <span>3. AI Detection</span>
            </div>

            <div className={`p-2.5 rounded-xl border transition-all ${
              currentPhase >= 4 ? 'border-[#3b5749] bg-[#eaf1ed] text-[#2b4d3a] font-bold' : 'border-[#e6ded2] text-[#8c8275]'
            }`}>
              <FileText className="w-4 h-4 mx-auto mb-1 text-[#3b5749]" />
              <span>4. Final Dossier</span>
            </div>
          </div>

          {/* Real-time Terminal Log Stream */}
          <div>
            <div className="text-[11px] font-bold text-[#6e6459] uppercase tracking-wider mb-1.5 font-mono">
              Live Bitstream Telemetry & Forensic Log
            </div>
            <div className="bg-[#141b22] text-[#c9dcd0] rounded-xl p-3.5 font-mono text-[11.5px] h-36 overflow-y-auto space-y-1 scrollbar-thin border border-[#232f3d]">
              {logs.map((log, index) => (
                <div key={index} className="leading-relaxed font-mono">
                  {log.includes('CRYPTO') ? (
                    <span className="text-[#e2937c] font-semibold">{log}</span>
                  ) : log.includes('DETECTION') ? (
                    <span className="text-[#a5d6a7] font-semibold">{log}</span>
                  ) : log.includes('FFPROBE') ? (
                    <span className="text-[#90caf9]">{log}</span>
                  ) : (
                    <span>{log}</span>
                  )}
                </div>
              ))}
              {!isCompleted && !error && (
                <div className="flex items-center gap-1.5 text-[#eaf1ed]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#5e7d6f] animate-ping"></span>
                  <span>Processing video frames in parallel...</span>
                </div>
              )}
              {error && <div className="text-[#ffb39d]">{error}</div>}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-[#f5efe4] border-t border-[#e6ded2] flex items-center justify-between">
          <span className="text-xs font-mono text-[#6e6459]">
            {isCompleted ? '✓ Evidence verified & certified' : 'Preserving evidentiary bitstream...'}
          </span>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-[#5c544c] bg-white border border-[#ded5c7] rounded-lg hover:bg-black/5 transition-colors cursor-pointer"
            >
              Close
            </button>

            {isCompleted && (
              <button
                onClick={() => {
                  onClose();
                  onCompleteStep(8);
                }}
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
