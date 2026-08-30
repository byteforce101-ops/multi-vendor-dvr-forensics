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
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="w-full bg-white rounded-2xl border border-[#d2ecd6] p-6 sm:p-7 shadow-xs"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 mb-6 border-b border-[#e3f6e6]">
        <div>
          <h2 className="text-lg font-bold text-[#011405] tracking-tight">
            Evidence Ingest & Verification
          </h2>
          <p className="text-xs text-[#2d4a34] mt-0.5">
            ISO/IEC 27037 compliant intake • SHA-256 cryptographic preservation
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#e6faea] text-[#011405] border border-[#bde3c3]">
            WORM Locked Storage
          </span>
        </div>
      </div>

      <div className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-[#011405] mb-1.5">
              Case Identifier
            </label>
            <input
              value={caseName}
              onChange={(e) => setCaseName(e.target.value)}
              className="w-full rounded-lg bg-[#f7fef8] border border-[#d2ecd6] px-3.5 py-2 text-xs text-[#011405] font-medium focus:bg-white focus:border-[#415ef4] focus:outline-none transition-colors"
              placeholder="e.g. V-2024-081A"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#011405] mb-1.5">
              Evidence Tag (Optional)
            </label>
            <input
              value={evidenceId}
              onChange={(e) => setEvidenceId(e.target.value)}
              className="w-full rounded-lg bg-[#f7fef8] border border-[#d2ecd6] px-3.5 py-2 text-xs text-[#011405] font-medium focus:bg-white focus:border-[#415ef4] focus:outline-none transition-colors"
              placeholder="e.g. EVD-CAM-01"
            />
          </div>
        </div>

        {/* Dropzone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all ${
            isDragging
              ? 'border-[#1cf243] bg-[#e6faea]'
              : 'border-[#c2e4c8] bg-[#f7fef8] hover:bg-[#e8f9ec]/60 hover:border-[#1cf243]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="video/*,.mp4,.avi,.mov,.mkv,.dd,.raw,.dat,.bin"
            onChange={handleInputChange}
          />

          <div className="w-12 h-12 mx-auto rounded-xl bg-[#e6faea] text-[#16d639] flex items-center justify-center mb-3">
            <UploadCloud className="w-6 h-6" />
          </div>

          <h3 className="text-sm font-bold text-[#011405]">
            Drop evidence video or disk image here
          </h3>

          <p className="text-xs text-[#2d4a34] mt-1">
            Hikvision/HeimVision dumps (.dd, .dat), MP4, AVI, MOV, MKV up to 4GB
          </p>
        </div>

        {isHashing && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#e6faea] border border-[#bde3c3] text-xs text-[#011405] font-medium">
            <RefreshCw className="w-4 h-4 animate-spin text-[#16d639]" />
            <span>Calculating client-side SHA-256 integrity checksum...</span>
          </div>
        )}

        {selectedFile && (
          <div className="rounded-xl border border-[#d2ecd6] bg-[#f7fef8] p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-lg bg-[#e6faea] text-[#011405] border border-[#d2ecd6] flex items-center justify-center shrink-0">
                  <FileVideo className="w-5 h-5 text-[#415ef4]" />
                </div>

                <div className="min-w-0">
                  <h4 className="font-semibold text-xs text-[#011405] truncate">
                    {selectedFile.name}
                  </h4>
                  <p className="text-[11px] text-[#2d4a34]">
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
                className="p-1 text-[#55785d] hover:text-[#011405] hover:bg-[#e8f9ec] rounded-md transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="pt-2.5 border-t border-[#d2ecd6] flex items-center gap-2 text-xs">
              <CheckCircle2 className="w-4 h-4 text-[#16d639] shrink-0" />
              <div className="min-w-0 flex-1">
                <span className="text-[10px] uppercase font-bold text-[#16d639]">
                  SHA-256 Checksum:
                </span>
                <p className="truncate text-[#011405] font-mono text-[11px] mt-0.5">
                  {selectedFile.hash}
                </p>
              </div>
            </div>
          </div>
        )}

        {validationError && (
          <p className="text-xs text-rose-700 bg-rose-50 p-3 rounded-lg border border-rose-200">
            {validationError}
          </p>
        )}

        <div className="flex justify-end pt-2">
          <button
            id="btn-begin-processing"
            type="button"
            onClick={handleSubmit}
            disabled={isHashing}
            className="btn-universe-gradient px-6 py-2.5 rounded-lg text-xs font-semibold tracking-wide flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <span>Run Forensic Pipeline</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </motion.section>
  );
};
