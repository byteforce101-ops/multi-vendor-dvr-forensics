import React, { useState, useRef } from 'react';
import { UploadCloud, ArrowRight, FileVideo, CheckCircle2, X, RefreshCw, ShieldAlert, Sparkles, Database } from 'lucide-react';
import { motion } from 'motion/react';
import { EvidenceFile } from '../types';

interface UploadSectionProps {
  onBeginProcessing: (data: { caseName: string; evidenceId: string; file: EvidenceFile | null }) => void;
  onFileUploaded?: (file: EvidenceFile) => void;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  onBeginProcessing,
  onFileUploaded,
}) => {
  const [caseName, setCaseName] = useState('V-2024-081A');
  const [evidenceId, setEvidenceId] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<EvidenceFile | null>(null);
  const [isHashing, setIsHashing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Generates a mock SHA-256 hash from file attributes
  const generateSimulatedHash = (fileName: string, size: number) => {
    const chars = '0123456789abcdef';
    let hash = '';
    const seed = fileName + size.toString();
    for (let i = 0; i < 64; i++) {
      const charCode = seed.charCodeAt(i % seed.length) || (i * 7);
      hash += chars[(charCode * (i + 13)) % 16];
    }
    return hash;
  };

  const handleFile = (file: File) => {
    setIsHashing(true);
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(1);
    const sizeFormatted = file.size > 1024 * 1024 * 1024 
      ? `${(file.size / (1024 * 1024 * 1024)).toFixed(2)} GB` 
      : `${sizeInMB} MB`;

    setTimeout(() => {
      const hash = generateSimulatedHash(file.name, file.size);
      const newFile: EvidenceFile = {
        id: `evd-${Date.now().toString(36)}`,
        name: file.name,
        caseId: caseName || 'V-2024-081A',
        size: sizeFormatted,
        rawSizeBytes: file.size,
        uploadedAt: new Date().toISOString(),
        hash: hash,
        status: 'verified',
        codec: file.name.endsWith('.mov') ? 'ProRes / H.264 (avc1)' : 'H.264 (High) / AAC',
        duration: '00:18:42',
        resolution: '1920x1080 (1080p)',
        telemetry: {
          fps: 29.97,
          audioChannels: 2,
          bitrate: '14.2 Mbps',
          gps: '37.7749° N, 122.4194° W',
        },
      };

      setSelectedFile(newFile);
      setIsHashing(false);
      if (onFileUploaded) {
        onFileUploaded(newFile);
      }
    }, 600);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onBeginProcessing({
      caseName: caseName || 'V-2024-081A',
      evidenceId: evidenceId || `EVD-${Math.floor(100000 + Math.random() * 900000)}`,
      file: selectedFile,
    });
  };

  return (
    <motion.div 
      whileHover={{ y: -4, scale: 1.008 }}
      transition={{ duration: 0.25 }}
      className="w-full bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] hover:border-[#1b4e39]/35 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] hover:shadow-[0_20px_35px_-8px_rgba(34,30,27,0.1)] p-6 sm:p-8 flex flex-col justify-between transition-all"
    >
      <div>
        {/* Title */}
        <h2 className="text-[24px] sm:text-[26px] font-normal tracking-[-0.015em] text-[#221e1b] font-['EB_Garamond',serif]">
          Upload Evidence
        </h2>
        <p className="text-[13.5px] text-[#5c544c] mt-1 font-['Manrope',sans-serif]">
          Securely upload video files. Original metadata will be preserved prior to analysis.
        </p>

        {/* Input Fields Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
          <div>
            <label 
              htmlFor="case-name-input"
              className="block text-[11.5px] font-bold text-[#4a423a] mb-1.5 uppercase tracking-wider"
            >
              Case Name
            </label>
            <input
              id="case-name-input"
              type="text"
              value={caseName}
              onChange={(e) => setCaseName(e.target.value)}
              placeholder="e.g. V-2024-081A"
              className="w-full px-3.5 py-2.5 bg-[#fffdfa] border border-[#ded4c5] rounded-xl text-[13.5px] text-[#221e1b] placeholder-[#a69c90] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/20 focus:border-[#0f2338] transition-all font-mono shadow-2xs"
            />
          </div>

          <div>
            <label 
              htmlFor="evidence-id-input"
              className="block text-[11.5px] font-bold text-[#4a423a] mb-1.5 uppercase tracking-wider"
            >
              Evidence ID
            </label>
            <input
              id="evidence-id-input"
              type="text"
              value={evidenceId}
              onChange={(e) => setEvidenceId(e.target.value)}
              placeholder="Auto-generated if left blank"
              className="w-full px-3.5 py-2.5 bg-[#fffdfa] border border-[#ded4c5] rounded-xl text-[13.5px] text-[#221e1b] placeholder-[#a69c90] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/20 focus:border-[#0f2338] transition-all font-mono shadow-2xs"
            />
          </div>
        </div>

        {/* Drag & Drop Upload Zone */}
        <div className="mt-5">
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/x-msvideo,.mp4,.mov,.avi"
            onChange={handleFileChange}
            className="hidden"
            id="evidence-file-input"
          />

          {!selectedFile ? (
            <motion.div
              id="dropzone-evidence"
              whileHover={{ scale: 1.025, y: -2 }}
              transition={{ duration: 0.2 }}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`w-full rounded-2xl border-2 border-dashed transition-all cursor-pointer p-8 sm:p-10 flex flex-col items-center justify-center text-center shadow-xs hover:shadow-md ${
                isDragging
                  ? 'border-[#1b4e39] bg-[#eaf1ed]/80 scale-[0.99]'
                  : 'border-[#b6cdc0] upload-zone-sage-gradient hover:border-[#236446]'
              }`}
            >
              {/* Cloud Icon with upload arrow */}
              <div className="w-12 h-12 rounded-full bg-white shadow-xs flex items-center justify-center text-[#3b5749] mb-3 border border-[#ded4c5]">
                <UploadCloud className="w-6 h-6 stroke-[1.8]" />
              </div>

              <div className="text-[16px] font-semibold text-[#221e1b] tracking-tight">
                Drag & Drop files here
              </div>

              <div className="text-[13px] text-[#635b52] mt-0.5">
                or <span className="text-[#1b4e39] font-bold hover:underline">browse files</span>
              </div>

              {/* Format Badge Pill */}
              <div className="mt-4 px-4 py-1.5 bg-white/90 backdrop-blur-xs border border-[#ded4c5] rounded-full text-[11.5px] font-semibold text-[#4a423a] tracking-wide">
                MP4, MOV, AVI up to 50GB
              </div>
            </motion.div>
          ) : (
            <div className="w-full rounded-2xl border border-[#c9dcd0] bg-[#eef4f0] p-4 sm:p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3.5">
                  <div className="w-11 h-11 rounded-xl bg-[#0f2338] text-white flex items-center justify-center shadow-xs">
                    <FileVideo className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-[14px] font-bold text-[#221e1b] truncate max-w-[260px] sm:max-w-md">
                      {selectedFile.name}
                    </h4>
                    <p className="text-[12px] text-[#5c544c] mt-0.5 font-mono">
                      {selectedFile.size} • {selectedFile.codec}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="p-1 text-[#7d7367] hover:text-[#221e1b] rounded-lg hover:bg-black/5"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Hash status indicator */}
              <div className="mt-3.5 pt-3 border-t border-[#c9dcd0] flex items-center justify-between text-[11.5px]">
                <div className="flex items-center space-x-1.5 text-[#2b4d3a] font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#3b5749]" />
                  <span className="font-bold">SHA-256 Bitstream Sealed:</span>
                  <span className="truncate max-w-[150px] sm:max-w-[240px] text-[#4a423a]">
                    {selectedFile.hash}
                  </span>
                </div>
                <span className="text-[#5c544c] font-mono hidden sm:inline font-semibold">100% Bit-Preserved</span>
              </div>
            </div>
          )}

          {isHashing && (
            <div className="mt-3 flex items-center justify-center space-x-2 text-xs text-[#3b5749] font-mono animate-pulse">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Calculating SHA-256 integrity hash and extracting metadata...</span>
            </div>
          )}
        </div>
      </div>

      {/* Begin Processing Button - Primary Rich Forest Green CTA */}
      <div className="mt-6 flex justify-end">
        <button
          id="btn-begin-processing"
          type="button"
          onClick={handleSubmit}
          className="btn-primary-green px-6 py-3 rounded-full text-white text-[14px] font-semibold flex items-center space-x-2 tracking-wide cursor-pointer group"
        >
          <span>Begin Processing</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform stroke-[2.3]" />
        </button>
      </div>
    </motion.div>
  );
};
