import React, { useState } from 'react';
import { ShieldCheck, FileVideo, CheckCircle, ChevronDown, ChevronUp, Lock, ExternalLink, Hash } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { EvidenceFile } from '../types';

interface ChainOfCustodyProps {
  recentFiles: EvidenceFile[];
  onOpenActivityLog: () => void;
  onSelectFile?: (file: EvidenceFile) => void;
}

export const ChainOfCustody: React.FC<ChainOfCustodyProps> = ({
  recentFiles,
  onOpenActivityLog,
  onSelectFile,
}) => {
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedFileId(expandedFileId === id ? null : id);
  };

  return (
    <motion.div 
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ duration: 0.25 }}
      className="w-full bg-[#f3f7f4] border border-[#d2e2d8] hover:border-[#1b4e39]/35 rounded-2xl p-6 sm:p-7 relative overflow-hidden flex flex-col justify-between shadow-[0_4px_20px_-4px_rgba(34,30,27,0.04)] hover:shadow-[0_16px_30px_-6px_rgba(27,78,57,0.1)] transition-all"
    >
      {/* Decorative Watermark Shield in Top-Right */}
      <div className="absolute -top-3 -right-3 text-[#cbdcd2] pointer-events-none select-none opacity-75" aria-hidden="true">
        <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      </div>

      <div className="relative z-10">
        {/* Title */}
        <h3 className="text-[20px] sm:text-[21px] font-semibold text-[#221e1b] font-['EB_Garamond',serif] tracking-tight">
          Chain of Custody
        </h3>

        {/* Informational Subtext */}
        <p className="text-[13px] text-[#5c544c] mt-1.5 leading-relaxed font-['Manrope',sans-serif]">
          Every file uploaded is immediately hashed (SHA-256) upon receipt. The original bitstream is stored in immutable cold storage.
        </p>

        {/* Recent Uploads Header */}
        <div className="mt-6 mb-3 flex items-center justify-between">
          <span className="text-[11.5px] font-bold text-[#4a423a] uppercase tracking-wider">
            Recent Uploads
          </span>
          <span className="text-[10.5px] font-mono text-[#3b5749] bg-[#eaf1ed] border border-[#c9dcd0] px-2.5 py-0.5 rounded-full font-semibold">
            256-Bit Cryptosealed
          </span>
        </div>

        {/* Uploads List */}
        <div className="space-y-2.5">
          {recentFiles.map((file) => {
            const isExpanded = expandedFileId === file.id;

            return (
              <motion.div
                key={file.id}
                whileHover={{ scale: 1.02, y: -2 }}
                transition={{ duration: 0.2 }}
                className="bg-[#fcfbf8] hover:bg-[#ffffff] rounded-xl border border-[#ded5c7] hover:border-[#1b4e39]/40 p-3.5 transition-all shadow-2xs hover:shadow-md group cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div 
                    className="flex items-center space-x-3 min-w-0 cursor-pointer flex-1"
                    onClick={() => {
                      toggleExpand(file.id);
                      if (onSelectFile) onSelectFile(file);
                    }}
                  >
                    {/* Video Icon container */}
                    <div className="w-8 h-8 rounded-lg bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center flex-shrink-0 group-hover:bg-[#dce9e1] transition-colors">
                      <FileVideo className="w-4 h-4" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-bold text-[#221e1b] truncate">
                        {file.name}
                      </div>
                      <div className="text-[11.5px] text-[#6e6459] font-mono flex items-center gap-1.5">
                        <span>{file.size}</span>
                        <span>•</span>
                        <span className="text-[#4a423a] font-medium">Case: {file.caseId}</span>
                      </div>
                    </div>
                  </div>

                  {/* Verification Dropdown Icon */}
                  <button
                    id={`toggle-file-${file.id}`}
                    onClick={() => toggleExpand(file.id)}
                    className="p-1 text-[#7d7367] hover:text-[#221e1b] rounded-md transition-colors ml-2 cursor-pointer"
                    aria-label="Toggle file hash details"
                  >
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {/* Expanded Forensic Metadata */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-3 pt-2.5 border-t border-[#ede5d8] text-[11px] font-mono text-[#5c544c] space-y-1.5 overflow-hidden"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[#8c8275]">HASH (SHA-256):</span>
                        <span className="font-semibold text-[#221e1b] truncate max-w-[180px]">
                          {file.hash}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[#8c8275]">TIMESTAMP:</span>
                        <span>{new Date(file.uploadedAt).toLocaleString()}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[#8c8275]">STATUS:</span>
                        <span className="text-[#2b4d3a] font-semibold flex items-center gap-1">
                          <CheckCircle className="w-3 h-3 text-[#3b5749]" /> Bitstream Verified
                        </span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* View Activity Log link */}
      <div className="mt-6 pt-2 relative z-10">
        <button
          id="btn-view-activity-log"
          onClick={onOpenActivityLog}
          className="text-[13px] font-semibold text-[#0f2338] hover:text-[#c2593f] hover:underline flex items-center space-x-1.5 transition-colors group cursor-pointer"
        >
          <span>View Activity Log</span>
          <ExternalLink className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform opacity-75" />
        </button>
      </div>
    </motion.div>
  );
};
