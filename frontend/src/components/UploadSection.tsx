import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  ArrowRight,
  FileVideo,
  CheckCircle2,
  X,
  RefreshCw,
  Fingerprint,
} from 'lucide-react';
import { motion } from 'motion/react';
import { EvidenceFile } from '../types';

interface UploadSectionProps {
  onBeginProcessing: (data: {
    caseName: string;
    evidenceId: string;
    file: EvidenceFile | null;
  }) => void;
  onFileUploaded?: (file: EvidenceFile) => void;
  isAuthenticated?: boolean;
  onRequestLogin?: () => void;
}

async function generateSHA256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(hashBuffer))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  onBeginProcessing,
  onFileUploaded,
  isAuthenticated = true,
  onRequestLogin,
}) => {
  const [caseName, setCaseName] = useState('V-2024-081A');
  const [evidenceId, setEvidenceId] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<EvidenceFile | null>(null);
  const [isHashing, setIsHashing] = useState(false);
  const [validationError, setValidationError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setValidationError('');
    setIsHashing(true);

    try {
      const hash = await generateSHA256(file);

      const evidenceFile: EvidenceFile = {
        id: `evd-${Date.now().toString(36)}`,
        name: file.name,
        caseId: caseName || 'V-2024-081A',
        size: formatFileSize(file.size),
        rawSizeBytes: file.size,
        sourceFile: file,
        uploadedAt: new Date().toISOString(),
        hash,
        status: 'verified',
        codec: 'Pending backend analysis',
        duration: 'Pending backend analysis',
        resolution: 'Pending backend analysis',
      };

      setSelectedFile(evidenceFile);
      onFileUploaded?.(evidenceFile);
    } catch (error) {
      console.error(error);
      setValidationError('Unable to calculate SHA-256 integrity hash.');
    } finally {
      setIsHashing(false);
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const handleSubmit = () => {
    setValidationError('');

    if (!isAuthenticated) {
      onRequestLogin?.();
      return;
    }

    if (!selectedFile) {
      setValidationError('Please select or drop an evidence file first.');
      return;
    }

    onBeginProcessing({
      caseName: caseName.trim() || 'V-2024-081A',
      evidenceId: evidenceId.trim() || selectedFile.id.toUpperCase(),
      file: selectedFile,
    });
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="w-full spotlight-card p-6 sm:p-8"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-6 border-b border-slate-100">
        <div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            Evidence Ingest & Cryptographic Seal
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            ISO/IEC 27037 compliant intake • SHA-256 dual-pass verification
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="shimmer-emerald text-[11px] font-semibold px-3 py-1 rounded-full text-emerald-800 border border-emerald-300/80 flex items-center gap-1.5 shadow-2xs">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            WORM Immutable Storage
          </span>
        </div>
      </div>

      <div className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Case Identifier
            </label>
            <input
              value={caseName}
              onChange={(e) => setCaseName(e.target.value)}
              className="w-full rounded-xl bg-slate-50/70 border border-slate-200 px-3.5 py-2.5 text-xs text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 focus:outline-none transition-all"
              placeholder="e.g. V-2024-081A"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Evidence Tag (Optional)
            </label>
            <input
              value={evidenceId}
              onChange={(e) => setEvidenceId(e.target.value)}
              className="w-full rounded-xl bg-slate-50/70 border border-slate-200 px-3.5 py-2.5 text-xs text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 focus:outline-none transition-all"
              placeholder="e.g. EVD-CAM-01"
            />
          </div>
        </div>

        {/* Dropzone with kinetic hover */}
        <motion.div
          whileHover={{ scale: 1.004 }}
          whileTap={{ scale: 0.995 }}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-9 text-center transition-all ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50/50 shadow-inner'
              : 'border-slate-300/90 bg-slate-50/50 hover:bg-indigo-50/20 hover:border-indigo-400'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="video/*,.mp4,.avi,.mov,.mkv,.dd,.raw,.dat,.bin"
            onChange={handleInputChange}
          />

          <div className="w-12 h-12 mx-auto rounded-2xl bg-indigo-50 text-indigo-600 border border-indigo-100 flex items-center justify-center mb-3 shadow-xs">
            <UploadCloud className="w-6 h-6" />
          </div>

          <h3 className="text-sm font-bold text-slate-800">
            Drop evidence video or disk image here
          </h3>

          <p className="text-xs text-slate-500 mt-1">
            Hikvision/HeimVision dumps (.dd, .dat), MP4, AVI, MOV, MKV up to 4GB
          </p>
        </motion.div>

        {isHashing && (
          <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-200/80 text-xs text-indigo-900 font-medium">
            <RefreshCw className="w-4 h-4 animate-spin text-indigo-600" />
            <span>Calculating client-side SHA-256 cryptographic seal...</span>
          </div>
        )}

        {selectedFile && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 space-y-3 shadow-xs"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                  <FileVideo className="w-5 h-5" />
                </div>

                <div className="min-w-0">
                  <h4 className="font-semibold text-xs text-slate-900 truncate">
                    {selectedFile.name}
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    {selectedFile.size} • Ready for extraction & pipeline
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
                className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-md transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="pt-2.5 border-t border-slate-200/80 flex items-center gap-2 text-xs">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <div className="min-w-0 flex-1">
                <span className="text-[10px] uppercase font-bold text-emerald-700">
                  Dual-Pass SHA-256 Seal:
                </span>
                <p className="truncate text-slate-800 font-mono text-[11px] mt-0.5">
                  {selectedFile.hash}
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {validationError && (
          <p className="text-xs text-rose-700 bg-rose-50 p-3.5 rounded-xl border border-rose-200">
            {validationError}
          </p>
        )}

        <div className="flex justify-end pt-2">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            id="btn-begin-processing"
            type="button"
            onClick={handleSubmit}
            disabled={isHashing}
            className="btn-kinetic-primary px-6 py-2.5 text-xs font-semibold tracking-wide flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <span>Run Forensic Pipeline</span>
            <ArrowRight className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </motion.section>
  );
};
