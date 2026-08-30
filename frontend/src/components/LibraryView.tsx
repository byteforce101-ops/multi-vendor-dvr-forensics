import React, { useState } from 'react';
import { Search, FileVideo, ShieldCheck, Download, CheckCircle2, ChevronRight } from 'lucide-react';
import { motion } from 'motion/react';
import { EvidenceFile } from '../types';

interface LibraryViewProps {
  files: EvidenceFile[];
  onOpenActivityLog: () => void;
  onOpenDetails?: (file: EvidenceFile) => void;
}

export const LibraryView: React.FC<LibraryViewProps> = ({
  files,
  onOpenActivityLog,
  onOpenDetails,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = files.filter(
    (f) =>
      f.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.caseId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.hash.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleExportManifest = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(files, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `tracex-evidence-manifest-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      {/* Vault Header */}
      <div className="bg-white rounded-2xl border border-[#d2ecd6] p-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#e6faea] text-[#011405] border border-[#bde3c3]">
            Immutable Storage
          </span>
          <h2 className="text-xl font-bold text-[#011405] mt-1.5 tracking-tight">
            Evidence Vault & Archive
          </h2>
          <p className="text-xs text-[#2d4a34] mt-0.5">
            Cryptographically sealed repository • ISO/IEC 27037 compliant audit trail
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={handleExportManifest}
            className="btn-universe-gradient px-4 py-2 rounded-lg text-xs font-semibold tracking-wide flex items-center gap-2 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Manifest</span>
          </button>

          <button
            onClick={onOpenActivityLog}
            className="px-3.5 py-2 rounded-lg bg-[#f7fef8] hover:bg-[#e8f9ec] border border-[#d2ecd6] text-[#011405] text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-[#16d639]" />
            <span>Chain of Custody</span>
          </button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white rounded-xl border border-[#d2ecd6] p-3 shadow-xs flex items-center justify-between gap-3">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-[#55785d] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by filename, case ID, or SHA-256 hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#f7fef8] border border-[#d2ecd6] rounded-lg text-xs text-[#011405] placeholder-[#55785d] focus:outline-none focus:border-[#415ef4] focus:bg-white transition-colors"
          />
        </div>
        <div className="text-xs text-[#2d4a34] hidden sm:block font-medium">
          Showing <span className="text-[#011405] font-bold">{filtered.length}</span> of {files.length} records
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[#d2ecd6] p-12 text-center text-xs text-[#55785d] shadow-xs">
          No evidence records found in the current session vault. Ingest video files from the Evidence Ingest tab.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((item) => (
            <div
              key={item.id}
              onClick={() => onOpenDetails?.(item)}
              className="bg-white rounded-xl border border-[#d2ecd6] p-5 hover:border-[#1cf243] hover:shadow-md transition-all duration-200 flex flex-col justify-between cursor-pointer space-y-3 shadow-xs"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="w-9 h-9 rounded-lg bg-[#e6faea] text-[#011405] border border-[#d2ecd6] flex items-center justify-center">
                    <FileVideo className="w-4.5 h-4.5 text-[#415ef4]" />
                  </div>
                  <span className="text-[10px] font-semibold text-[#011405] bg-[#e6faea] border border-[#bde3c3] px-2 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-[#16d639]" /> {item.status}
                  </span>
                </div>

                <h4 className="font-semibold text-xs text-[#011405] mt-3 truncate" title={item.name}>
                  {item.name}
                </h4>

                <div className="text-xs text-[#2d4a34] mt-1 space-y-0.5">
                  <div>Case ID: <span className="font-semibold text-[#011405]">{item.caseId}</span></div>
                  <div>File Size: {item.size}</div>
                </div>

                <div className="mt-3 p-2.5 bg-[#f7fef8] rounded-lg border border-[#e3f6e6] font-mono text-[11px] text-[#011405] break-all">
                  <span className="text-[#55785d] font-sans text-[10px] block uppercase font-semibold">SHA-256 Seal</span>
                  {item.hash ? `${item.hash.substring(0, 24)}...` : 'PENDING'}
                </div>
              </div>

              <div className="pt-3 border-t border-[#e3f6e6] flex items-center justify-between text-xs text-[#55785d]">
                <span>{new Date(item.uploadedAt).toLocaleDateString()}</span>
                <span className="text-[#415ef4] font-semibold flex items-center gap-1">
                  Inspect <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
};
