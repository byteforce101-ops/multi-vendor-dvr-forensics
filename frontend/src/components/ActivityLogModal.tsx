import React, { useState } from 'react';
import { X, ShieldCheck, Download, Search, CheckCircle2, Lock, FileText, ArrowUpDown } from 'lucide-react';
import { ActivityLogItem } from '../types';

interface ActivityLogModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SAMPLE_LOGS: ActivityLogItem[] = [
  {
    id: 'act-99201',
    timestamp: '2024-10-24 14:22:18 UTC',
    action: 'SHA-256 Seal & Cold Ingestion',
    fileName: 'Interrogation_RM3_A.mp4',
    caseId: 'V-050',
    hashSnippet: 'e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934ca495991b7852b855',
    operator: 'Enterprise User (10D11A8)',
    verified: true,
  },
  {
    id: 'act-99200',
    timestamp: '2024-10-24 11:05:42 UTC',
    action: 'Container Demux & Codec Dissection',
    fileName: 'Dashcam_Unit42.mov',
    caseId: 'V-079',
    hashSnippet: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
    operator: 'Enterprise User (10D11A8)',
    verified: true,
  },
  {
    id: 'act-99199',
    timestamp: '2024-10-23 18:40:11 UTC',
    action: 'Automated Event Timeline Extraction',
    fileName: 'Bodycam_Officer_71.mp4',
    caseId: 'V-041',
    hashSnippet: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
    operator: 'Lead Investigator J. Vance',
    verified: true,
  },
  {
    id: 'act-99198',
    timestamp: '2024-10-23 09:12:05 UTC',
    action: 'Case Initialized & Custody Transferred',
    fileName: 'CCTV_Entrance_West.avi',
    caseId: 'V-038',
    hashSnippet: 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
    operator: 'System Daemon (Auto-Hashed)',
    verified: true,
  },
];

export const ActivityLogModal: React.FC<ActivityLogModalProps> = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');

  if (!isOpen) return null;

  const filteredLogs = SAMPLE_LOGS.filter(
    (log) =>
      log.fileName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.caseId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.action.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleExportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(SAMPLE_LOGS, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `visionstream-chain-of-custody-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1e1b18]/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#fcfbf8] rounded-2xl max-w-4xl w-full border border-[#e6ded2] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-[#e6ded2] flex items-center justify-between bg-[#f5efe4]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-[19px] font-semibold text-[#221e1b] font-['DM_Sans',sans-serif]">
                Chain of Custody — Cryptographic Ledger
              </h3>
              <p className="text-xs text-[#6e6459] font-mono">
                Immutable SHA-256 audit log certified under ISO/IEC 27037 & CJIS Level 4
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#8c8275] hover:text-[#221e1b] rounded-lg hover:bg-black/5 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="px-6 py-3.5 border-b border-[#e6ded2] bg-[#fcfbf8] flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-[#8c8275] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by filename, case ID, or event..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 bg-[#fffdfa] border border-[#dcd4c7] rounded-xl text-xs text-[#221e1b] placeholder-[#9c9489] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/30 font-mono"
            />
          </div>

          <button
            onClick={handleExportJSON}
            className="w-full sm:w-auto px-4 py-2 bg-white border border-[#ded5c7] hover:bg-[#f5efe4] text-[#221e1b] rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-2xs"
          >
            <Download className="w-3.5 h-3.5 text-[#0f2338]" />
            <span>Export Certified Ledger (JSON)</span>
          </button>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto flex-1 p-6">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[#e6ded2] text-[#7d7367]">
                <th className="pb-3 font-bold">TIMESTAMP</th>
                <th className="pb-3 font-bold">ACTION</th>
                <th className="pb-3 font-bold">EVIDENCE FILE</th>
                <th className="pb-3 font-bold">CASE</th>
                <th className="pb-3 font-bold">OPERATOR</th>
                <th className="pb-3 font-bold text-right">BITSTREAM INTEGRITY</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ede5d8]">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-[#f5efe4]/80 transition-colors">
                  <td className="py-3.5 text-[#6e6459] whitespace-nowrap">{log.timestamp}</td>
                  <td className="py-3.5 font-bold text-[#221e1b]">{log.action}</td>
                  <td className="py-3.5 text-[#0f2338] font-bold">{log.fileName}</td>
                  <td className="py-3.5 text-[#6e6459]">{log.caseId}</td>
                  <td className="py-3.5 text-[#6e6459] truncate max-w-[140px]">{log.operator}</td>
                  <td className="py-3.5 text-right">
                    <span className="inline-flex items-center gap-1 text-[#2b4d3a] bg-[#eaf1ed] border border-[#c9dcd0] px-2.5 py-0.5 rounded-full font-bold text-[11px]">
                      <CheckCircle2 className="w-3 h-3 text-[#3b5749]" />
                      SHA-256 Valid
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[#f5efe4] border-t border-[#e6ded2] flex items-center justify-between text-xs text-[#6e6459] font-mono">
          <span>Total Recorded Ledger Entries: {filteredLogs.length}</span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white border border-[#ded5c7] rounded-lg text-[#221e1b] font-bold hover:bg-black/5 cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
