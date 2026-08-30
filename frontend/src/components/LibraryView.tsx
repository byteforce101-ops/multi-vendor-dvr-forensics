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
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-6"
    >
      {/* Vault Header */}
      <div className="spotlight-card p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="shimmer-badge text-[11px] font-semibold px-2.5 py-0.5 rounded-full text-indigo-900 border border-indigo-200/80">
            Immutable Storage
          </span>
          <h2 className="text-xl font-bold text-slate-900 mt-1.5 tracking-tight">
            Evidence Vault & Manifest Archive
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographically sealed repository • ISO/IEC 27037 compliant audit trail
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleExportManifest}
            className="btn-kinetic-primary px-4 py-2 text-xs font-semibold tracking-wide flex items-center gap-2 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Manifest</span>
          </motion.button>

          <button
            onClick={onOpenActivityLog}
            className="px-3.5 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-medium flex items-center gap-2 transition-all cursor-pointer shadow-xs active:scale-98"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Chain of Custody</span>
          </button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="spotlight-card p-3 flex items-center justify-between gap-3">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by filename, case ID, or SHA-256 hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/10 transition-all"
          />
        </div>
        <div className="text-xs text-slate-500 hidden sm:block font-medium pr-2">
          Showing <span className="text-slate-900 font-bold">{filtered.length}</span> of {files.length} records
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="spotlight-card p-12 text-center text-xs text-slate-400">
          No evidence records found in the current session vault. Ingest video files from the Evidence Ingest tab.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((item) => (
            <motion.div
              key={item.id}
              whileHover={{ y: -2 }}
              onClick={() => onOpenDetails?.(item)}
              className="spotlight-card p-5 flex flex-col justify-between cursor-pointer space-y-3"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100 flex items-center justify-center">
                    <FileVideo className="w-4.5 h-4.5" />
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" /> {item.status}
                  </span>
                </div>

                <h4 className="font-semibold text-xs text-slate-900 mt-3 truncate" title={item.name}>
                  {item.name}
                </h4>

                <div className="text-xs text-slate-500 mt-1 space-y-0.5">
                  <div>Case ID: <span className="font-semibold text-slate-800">{item.caseId}</span></div>
                  <div>File Size: {item.size}</div>
                </div>

                <div className="mt-3 p-2.5 bg-slate-50 rounded-xl border border-slate-100 font-mono text-[11px] text-slate-700 break-all">
                  <span className="text-slate-400 font-sans text-[10px] block uppercase font-bold tracking-wider">Dual-Pass SHA-256 Seal</span>
                  {item.hash ? `${item.hash.substring(0, 24)}...` : 'PENDING'}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span>{new Date(item.uploadedAt).toLocaleDateString()}</span>
                <span className="text-indigo-600 font-semibold flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                  Inspect <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
};
