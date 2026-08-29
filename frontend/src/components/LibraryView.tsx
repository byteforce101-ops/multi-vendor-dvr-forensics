import React, { useState } from 'react';
import { Search, Filter, FileVideo, ShieldCheck, Download, MoreVertical, CheckCircle2, Lock } from 'lucide-react';
import { motion } from 'motion/react';
import { EvidenceFile } from '../types';

interface LibraryViewProps {
  files: EvidenceFile[];
  onOpenActivityLog: () => void;
}

export const LibraryView: React.FC<LibraryViewProps> = ({ files, onOpenActivityLog }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const allFiles: EvidenceFile[] = [
    ...files,
    {
      id: 'evd-seed-1',
      name: 'Interrogation_RM3_A.mp4',
      caseId: 'V-050',
      size: '5.2 GB',
      uploadedAt: '2024-10-24T14:22:18Z',
      hash: 'e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934ca495991b7852b855',
      status: 'verified',
      codec: 'H.264 High (avc1)',
      duration: '00:45:12',
    },
    {
      id: 'evd-seed-2',
      name: 'Dashcam_Unit42.mov',
      caseId: 'V-079',
      size: '1.1 GB',
      uploadedAt: '2024-10-24T11:05:42Z',
      hash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
      status: 'verified',
      codec: 'ProRes 422',
      duration: '00:12:04',
    },
    {
      id: 'evd-seed-3',
      name: 'Bodycam_Officer_71.mp4',
      caseId: 'V-041',
      size: '3.8 GB',
      uploadedAt: '2024-10-23T18:40:11Z',
      hash: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
      status: 'verified',
      codec: 'H.264 Baseline',
      duration: '01:10:33',
    },
  ];

  const filtered = allFiles.filter(
    (f) =>
      f.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.caseId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.hash.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <motion.div 
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] p-6 sm:p-8 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-mono font-bold text-[#3b5749] uppercase tracking-wider bg-[#eaf1ed] border border-[#c9dcd0] px-3 py-0.5 rounded-md">
            Evidence Vault & Archive
          </span>
          <h2 className="text-2xl sm:text-3xl font-['EB_Garamond',serif] text-[#221e1b] mt-2 font-normal">
            Certified Evidence Repository
          </h2>
          <p className="text-xs text-[#6e6459] font-mono mt-1">
            NIST FIPS 180-4 Bitstream Verified Immutable Assets
          </p>
        </div>

        <button
          onClick={onOpenActivityLog}
          className="px-4 py-2 bg-[#eaf1ed] hover:bg-[#dde9e2] text-[#221e1b] rounded-xl text-xs font-bold flex items-center gap-2 transition-colors border border-[#c9dcd0] self-start sm:self-auto cursor-pointer shadow-2xs"
        >
          <ShieldCheck className="w-4 h-4 text-[#3b5749]" />
          <span>View Master Ledger</span>
        </button>
      </div>

      {/* Filter bar */}
      <div className="bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] p-4 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] flex items-center justify-between gap-3">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-[#8c8275] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by filename, case ID, or SHA-256 hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-[#fffdfa] border border-[#dcd4c7] rounded-xl text-xs text-[#221e1b] placeholder-[#9c9489] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/30 font-mono"
          />
        </div>
        <div className="text-xs font-mono text-[#6e6459] hidden sm:block font-medium">
          Showing {filtered.length} of {allFiles.length} Records
        </div>
      </div>

      {/* Grid of Evidence Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((item, idx) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, delay: idx * 0.05 }}
            whileHover={{ y: -7, scale: 1.03 }}
            className="bg-[#fcfbf8] rounded-2xl border border-[#e6ded2] p-5.5 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)] hover:shadow-[0_20px_35px_-8px_rgba(34,30,27,0.14)] hover:border-[#1b4e39]/40 transition-all duration-300 flex flex-col justify-between cursor-pointer group"
          >
            <div>
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 rounded-xl bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center">
                  <FileVideo className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono text-[#2b4d3a] bg-[#eaf1ed] border border-[#c9dcd0] px-2.5 py-0.5 rounded-full flex items-center gap-1 font-bold">
                  <CheckCircle2 className="w-3 h-3 text-[#3b5749]" /> Sealed
                </span>
              </div>

              <h4 className="font-bold text-[#221e1b] text-sm mt-3.5 truncate" title={item.name}>
                {item.name}
              </h4>

              <div className="text-xs text-[#6e6459] font-mono mt-1 space-y-0.5">
                <div>Case: <span className="font-bold text-[#221e1b]">{item.caseId}</span></div>
                <div>Size: {item.size} • {item.codec || 'H.264'}</div>
              </div>

              <div className="mt-3 p-2.5 bg-[#f5efe4] rounded-xl font-mono text-[11px] text-[#4a423a] break-all border border-[#ded5c7]">
                <span className="text-[#8c8275]">SHA-256: </span>
                <span>{item.hash.substring(0, 24)}...</span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#ede5d8] flex items-center justify-between text-xs font-mono">
              <span className="text-[#8c8275]">{new Date(item.uploadedAt).toLocaleDateString()}</span>
              <button className="text-[#0f2338] hover:text-[#c2593f] font-bold flex items-center gap-1 cursor-pointer transition-colors">
                <Download className="w-3.5 h-3.5" /> Ingest Dossier
              </button>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};
