import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  ArrowRight,
  FileVideo,
  CheckCircle2,
  X,
  RefreshCw,
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

  const hashBuffer = await crypto.subtle.digest(
    'SHA-256',
    buffer,
  );

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
  const [selectedFile, setSelectedFile] =
    useState<EvidenceFile | null>(null);

  const [isHashing, setIsHashing] = useState(false);
  const [validationError, setValidationError] =
    useState('');

  const fileInputRef =
    useRef<HTMLInputElement>(null);

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

        // IMPORTANT:
        // This is the actual file sent later to FastAPI.
        sourceFile: file,

        uploadedAt: new Date().toISOString(),

        // Real browser-generated SHA-256 preview.
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

      setValidationError(
        'Unable to calculate the SHA-256 preview hash.',
      );
    } finally {
      setIsHashing(false);
    }
  };

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];

    if (file) {
      handleFile(file);
    }
  };

  const handleDrop = (
    event: React.DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault();

    setIsDragging(false);

    const file = event.dataTransfer.files?.[0];

    if (file) {
      handleFile(file);
    }
  };

  const handleSubmit = () => {
    setValidationError('');

    if (!isAuthenticated) {
      onRequestLogin?.();
      return;
    }

    if (!selectedFile) {
      setValidationError(
        'Select an evidence file before starting.',
      );

      return;
    }

    onBeginProcessing({
      caseName: caseName.trim() || 'Untitled Case',

      evidenceId:
        evidenceId.trim() ||
        selectedFile.id.toUpperCase(),

      file: selectedFile,
    });
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="w-full bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] shadow-sm p-5 sm:p-6"
    >
      <div className="mb-6">
        <p className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3b5749] mb-2">
          Evidence Intake
        </p>

        <h2 className="text-xl sm:text-2xl font-bold text-[#221e1b]">
          Secure forensic evidence
        </h2>

        <p className="text-sm text-[#6e6459] mt-1">
          Add case information and upload the original
          evidence file for backend processing.
        </p>
      </div>

      <div className="space-y-5">
        <div>
          <label className="block text-xs font-bold text-[#221e1b] mb-2">
            CASE NAME / ID
          </label>

          <input
            value={caseName}
            onChange={(event) =>
              setCaseName(event.target.value)
            }
            className="w-full rounded-xl border border-[#ded5c7] bg-white px-4 py-3 text-sm outline-none focus:border-[#3b5749]"
            placeholder="Enter case name"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-[#221e1b] mb-2">
            EVIDENCE ID
          </label>

          <input
            value={evidenceId}
            onChange={(event) =>
              setEvidenceId(event.target.value)
            }
            className="w-full rounded-xl border border-[#ded5c7] bg-white px-4 py-3 text-sm outline-none focus:border-[#3b5749]"
            placeholder="Optional evidence identifier"
          />
        </div>

        <div
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 sm:p-10 text-center transition-all ${
            isDragging
              ? 'border-[#3b5749] bg-[#eaf1ed]'
              : 'border-[#c9dcd0] bg-[#f8fbf9]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="video/*,.mp4,.avi,.mov,.mkv"
            onChange={handleInputChange}
          />

          <UploadCloud className="w-9 h-9 mx-auto text-[#3b5749]" />

          <h3 className="mt-3 font-bold text-[#221e1b]">
            Drop evidence here
          </h3>

          <p className="text-xs text-[#6e6459] mt-1">
            MP4, AVI, MOV, MKV or supported DVR exports
          </p>
        </div>

        {isHashing && (
          <div className="flex items-center gap-2 text-xs text-[#3b5749] font-mono">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Calculating SHA-256 integrity preview...
          </div>
        )}

        {selectedFile && (
          <div className="rounded-xl border border-[#c9dcd0] bg-[#f8fbf9] p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-[#0f2338] text-white flex items-center justify-center">
                  <FileVideo className="w-5 h-5" />
                </div>

                <div className="min-w-0">
                  <h4 className="font-bold text-sm text-[#221e1b] truncate">
                    {selectedFile.name}
                  </h4>

                  <p className="text-xs text-[#6e6459]">
                    {selectedFile.size}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  setSelectedFile(null);
                }}
                className="p-1 text-[#7d7367] hover:text-[#221e1b]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 pt-3 border-t border-[#c9dcd0] flex gap-2 text-xs font-mono">
              <CheckCircle2 className="w-4 h-4 text-[#3b5749] shrink-0" />

              <div className="min-w-0">
                <span className="font-bold">
                  SHA-256 preview:
                </span>

                <p className="truncate text-[#5c544c] mt-1">
                  {selectedFile.hash}
                </p>
              </div>
            </div>
          </div>
        )}

        {validationError && (
          <p className="text-sm text-red-600">
            {validationError}
          </p>
        )}

        <div className="flex justify-end">
          <button
            id="btn-begin-processing"
            type="button"
            onClick={handleSubmit}
            disabled={isHashing}
            className="px-6 py-3 rounded-full bg-[#1b4e39] text-white text-sm font-semibold flex items-center gap-2 hover:bg-[#143b2c] disabled:opacity-50"
          >
            <span>Start Processing</span>

            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </motion.section>
  );
};