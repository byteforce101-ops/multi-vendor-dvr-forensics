import React from 'react';
import { ShieldCheck, FileVideo, ExternalLink } from 'lucide-react';
import { motion } from 'motion/react';
import { EvidenceFile } from '../types';

interface ChainOfCustodyProps {
  recentFiles: EvidenceFile[];
  onOpenActivityLog: () => void;
}

export const ChainOfCustody: React.FC<ChainOfCustodyProps> = ({ recentFiles, onOpenActivityLog }) => {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ duration: 0.25 }}
      className="w-full bg-[#f3f7f4] border border-[#d2e2d8] rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-[0_4px_20px_-4px_rgba(34,30,27,0.04)]"
    >
      <div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#1b4e39]" />
          <h3 className="text-[17px] font-semibold text-[#221e1b] font-['DM_Sans',sans-serif]">
            Recent Files
          </h3>
        </div>

        {recentFiles.length === 0 ? (
          <p className="text-[13px] text-[#5c544c] mt-4">Nothing uploaded yet this session.</p>
        ) : (
          <div className="mt-4 space-y-2">
            {recentFiles.map((file) => (
              <div
                key={file.id}
                className="bg-[#fcfbf8] rounded-xl border border-[#ded5c7] p-3 flex items-center gap-3"
              >
                <div className="w-8 h-8 rounded-lg bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center flex-shrink-0">
                  <FileVideo className="w-4 h-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold text-[#221e1b] truncate">{file.name}</div>
                  <div className="text-[11px] text-[#6e6459] font-mono truncate">
                    {file.size} · {file.hash ? `${file.hash.slice(0, 12)}…` : 'unhashed'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={onOpenActivityLog}
        className="mt-5 text-[13px] font-semibold text-[#0f2338] hover:text-[#c2593f] flex items-center gap-1.5 transition-colors cursor-pointer"
      >
        <span>Activity Log</span>
        <ExternalLink className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  );
};