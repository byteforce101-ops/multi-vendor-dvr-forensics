import React, { useState, useRef } from 'react';
import { UploadCloud, ArrowRight, FileVideo, X } from 'lucide-react';
import { motion } from 'motion/react';

interface PendingFile {
  file: File;
  name: string;
  sizeLabel: string;
}

interface UploadSectionProps {
  onBeginProcessing: (data: { caseName: string; file: File }) => void;
  busy?: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes > 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const UploadSection: React.FC<UploadSectionProps> = ({ onBeginProcessing, busy = false }) => {
  const [caseName, setCaseName] = useState('V-2024-081A');
  const [isDragging, setIsDragging] = useState(false);
  const [pending, setPending] = useState<PendingFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setPending({ file, name: file.name, sizeLabel: formatBytes(file.size) });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) handleFile(e.dataTransfer.files[0]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pending) return;
    onBeginProcessing({ caseName: caseName || 'V-2024-081A', file: pending.file });
  };

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.008 }}
      transition={{ duration: 0.25 }}
      className="w-full bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] hover:border-[#1b4e39]/35 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] hover:shadow-[0_20px_35px_-8px_rgba(34,30,27,0.1)] p-6 sm:p-8 flex flex-col justify-between transition-all"
    >
      <div>
        <h2 className="text-[24px] sm:text-[26px] font-normal tracking-[-0.015em] text-[#221e1b] font-['DM_Sans',sans-serif]">
          Upload Evidence
        </h2>
        <p className="text-[13.5px] text-[#5c544c] mt-1 font-['DM_Sans',sans-serif]">
          Add a video file to begin. Hashing happens on the server.
        </p>

        <div className="mt-6">
          <label htmlFor="case-name-input" className="block text-[11.5px] font-bold text-[#4a423a] mb-1.5 uppercase tracking-wider">
            Case
          </label>
          <input
            id="case-name-input"
            type="text"
            value={caseName}
            onChange={(e) => setCaseName(e.target.value)}
            placeholder="e.g. V-2024-081A"
            className="w-full px-3.5 py-2.5 bg-[#fffdfa] border border-[#ded4c5] rounded-xl text-[13.5px] text-[#221e1b] placeholder-[#a69c90] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/20 focus:border-[#0f2338] transition-all font-mono shadow-2xs"
          />
          <p className="text-[11px] text-[#8c8275] mt-1">
            Reuses an existing case with this exact name, or creates a new one.
          </p>
        </div>

        <div className="mt-5">
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/x-msvideo,.mp4,.mov,.avi,.dd,.img,.bin,.dat"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            className="hidden"
            id="evidence-file-input"
          />

          {!pending ? (
            <motion.div
              id="dropzone-evidence"
              whileHover={{ scale: 1.02, y: -2 }}
              transition={{ duration: 0.2 }}
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
              onClick={() => fileInputRef.current?.click()}
              className={`w-full rounded-2xl border-2 border-dashed transition-all cursor-pointer p-8 sm:p-10 flex flex-col items-center justify-center text-center shadow-xs hover:shadow-md ${
                isDragging
                  ? 'border-[#1b4e39] bg-[#eaf1ed]/80 scale-[0.99]'
                  : 'border-[#b6cdc0] upload-zone-sage-gradient hover:border-[#236446]'
              }`}
            >
              <div className="w-12 h-12 rounded-full bg-white shadow-xs flex items-center justify-center text-[#3b5749] mb-3 border border-[#ded4c5]">
                <UploadCloud className="w-6 h-6 stroke-[1.8]" />
              </div>
              <div className="text-[16px] font-semibold text-[#221e1b] tracking-tight">Drop video here</div>
              <div className="text-[13px] text-[#635b52] mt-0.5">
                or <span className="text-[#1b4e39] font-bold hover:underline">browse</span>
              </div>
              <div className="mt-4 px-4 py-1.5 bg-white/90 backdrop-blur-xs border border-[#ded4c5] rounded-full text-[11.5px] font-semibold text-[#4a423a] tracking-wide">
                MP4, MOV, AVI, or raw .dd images
              </div>
            </motion.div>
          ) : (
            <div className="w-full rounded-2xl border border-[#c9dcd0] bg-[#eef4f0] p-4 sm:p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3.5 min-w-0">
                  <div className="w-11 h-11 rounded-xl bg-[#0f2338] text-white flex items-center justify-center shadow-xs flex-shrink-0">
                    <FileVideo className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-[14px] font-bold text-[#221e1b] truncate max-w-[260px] sm:max-w-md">
                      {pending.name}
                    </h4>
                    <p className="text-[12px] text-[#5c544c] mt-0.5 font-mono">{pending.sizeLabel}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setPending(null)}
                  disabled={busy}
                  className="p-1 text-[#7d7367] hover:text-[#221e1b] rounded-lg hover:bg-black/5 cursor-pointer disabled:opacity-50"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-3.5 pt-3 border-t border-[#c9dcd0] text-[11.5px] text-[#5c544c] font-mono">
                Not yet uploaded — SHA-256 will be computed once processing starts.
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          id="btn-begin-processing"
          type="button"
          onClick={handleSubmit}
          disabled={!pending || busy}
          className="btn-primary-green px-6 py-3 rounded-full text-white text-[14px] font-semibold flex items-center space-x-2 tracking-wide cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span>{busy ? 'Processing…' : 'Start'}</span>
          {!busy && <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform stroke-[2.3]" />}
        </button>
      </div>
    </motion.div>
  );
};