import React from 'react';
import { ShieldCheck, FileVideo, ExternalLink, Hash } from 'lucide-react';
import { motion } from 'motion/react';
import { EvidenceFile } from '../types';

interface ChainOfCustodyProps {
  recentFiles: EvidenceFile[];
  onOpenActivityLog: () => void;
}

export const ChainOfCustody: React.FC<ChainOfCustodyProps> = ({ recentFiles, onOpenActivityLog }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="w-full bg-[#08101E] border border-[#1E3A5F] rounded-lg p-5 flex flex-col justify-between"
    >
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-[#1E3A5F]">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#10B981]" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
              Session Custody Ledger
            </h3>
          </div>
          <span className="text-[10px] font-mono text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded border border-[#10B981]/30 font-semibold">
            {recentFiles.length} INGESTED
          </span>
        </div>

        {recentFiles.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-[#64748B]">
            No evidence bitstreams ingested in current session.
          </div>
        ) : (
          <div className="mt-3.5 space-y-2">
            {recentFiles.map((file) => (
              <div
                key={file.id}
                className="bg-[#0D192E] rounded border border-[#1E3A5F] p-2.5 flex items-center gap-3 hover:border-[#00D2FF]/40 transition-colors"
              >
                <div className="w-7 h-7 rounded bg-[#0284C7]/20 text-[#00D2FF] flex items-center justify-center shrink-0 border border-[#0284C7]/30">
                  <FileVideo className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold text-slate-200 truncate">{file.name}</div>
                  <div className="text-[10px] text-[#94A3B8] font-mono truncate flex items-center gap-1 mt-0.5">
                    <span>{file.size}</span>
                    <span>•</span>
                    <span className="text-[#00D2FF]">{file.hash ? `SHA256:${file.hash.slice(0, 10)}…` : 'PENDING'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={onOpenActivityLog}
        className="mt-4 pt-3 border-t border-[#1E3A5F] text-xs font-mono font-semibold text-[#00D2FF] hover:text-white flex items-center justify-between transition-colors cursor-pointer"
      >
        <span>Open Cryptographic Ledger</span>
        <ExternalLink className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  );
};