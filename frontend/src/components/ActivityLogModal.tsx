import React, { useState } from 'react';
import { X, ShieldCheck, Download, Search, CheckCircle2 } from 'lucide-react';
import { ActivityLogItem } from '../types';

interface ActivityLogModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SAMPLE_LOGS: ActivityLogItem[] = [
  {
    id: 'act-99201',
    timestamp: '2024-10-24 14:22:18 UTC',
    action: 'SHA-256 Bitstream Seal & Ingestion',
    fileName: 'Hikvision_DS7204_CH1.dd',
    caseId: 'V-2024-081A',
    hashSnippet: 'e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934ca495991b7852b855',
    operator: 'Lead Examiner S. Sharma',
    verified: true,
  },
  {
    id: 'act-99200',
    timestamp: '2024-10-24 11:05:42 UTC',
    action: 'Container Demux & Stream Extraction',
    fileName: 'HeimVision_H8_Segment_04.dat',
    caseId: 'V-2024-081A',
    hashSnippet: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
    operator: 'Lead Examiner S. Sharma',
    verified: true,
  },
  {
    id: 'act-99199',
    timestamp: '2024-10-23 18:40:11 UTC',
    action: 'Automated CV Timeline & Tracking Pass',
    fileName: 'CCTV_Perimeter_East.mp4',
    caseId: 'V-2024-072',
    hashSnippet: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
    operator: 'Automated Engine Daemon',
    verified: true,
  },
  {
    id: 'act-99198',
    timestamp: '2024-10-23 09:12:05 UTC',
    action: 'Evidence Ingested & WORM Locked',
    fileName: 'Entrance_Gate_Cam02.mkv',
    caseId: 'V-2024-070',
    hashSnippet: 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
    operator: 'Lead Examiner S. Sharma',
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
    downloadAnchor.setAttribute('download', `tracex-chain-of-custody-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-4xl w-full border border-slate-200 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                Chain of Custody — Cryptographic Ledger
              </h3>
              <p className="text-xs text-slate-500">
                Immutable SHA-256 audit log certified under ISO/IEC 27037 & NIST SP 800-86
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="px-6 py-3 border-b border-slate-100 bg-slate-50 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by filename, case ID, or event..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          <button
            onClick={handleExportJSON}
            className="btn-kinetic-primary w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Certified Ledger (JSON)</span>
          </button>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto flex-1 p-6">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-2.5 font-semibold">Timestamp</th>
                <th className="pb-2.5 font-semibold">Action</th>
                <th className="pb-2.5 font-semibold">Evidence File</th>
                <th className="pb-2.5 font-semibold">Case ID</th>
                <th className="pb-2.5 font-semibold">Operator</th>
                <th className="pb-2.5 font-semibold text-right">Integrity Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 text-slate-500 whitespace-nowrap font-mono text-[11px]">{log.timestamp}</td>
                  <td className="py-3 font-semibold text-slate-900">{log.action}</td>
                  <td className="py-3 text-indigo-600 font-medium">{log.fileName}</td>
                  <td className="py-3 text-slate-900">{log.caseId}</td>
                  <td className="py-3 text-slate-500 truncate max-w-[150px]">{log.operator}</td>
                  <td className="py-3 text-right">
                    <span className="inline-flex items-center gap-1 text-slate-900 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-semibold text-[10px]">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      SHA-256 SEAL VALID
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span>Recorded Ledger Entries: {filteredLogs.length}</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-900 text-xs font-medium hover:bg-slate-100 transition-colors cursor-pointer shadow-xs"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
