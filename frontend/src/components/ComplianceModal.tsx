import React, { useState } from 'react';
import { X, ShieldCheck, FileCheck, Code2, Lock, CheckCircle2, Copy, Check } from 'lucide-react';

interface ComplianceModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: 'security' | 'compliance' | 'api';
}

export const ComplianceModal: React.FC<ComplianceModalProps> = ({
  isOpen,
  onClose,
  initialTab = 'security',
}) => {
  const [activeTab, setActiveTab] = useState<'security' | 'compliance' | 'api'>(initialTab);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const sampleApiCall = `curl -X POST http://localhost:8000/video/analyze \\
  -H "Authorization: Bearer <JWT_TOKEN>" \\
  -F "file=@Hikvision_DS7204_CH1.dd"`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-3xl w-full border border-[#d2ecd6] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#e3f6e6] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-[#011405] flex items-center justify-center">
              {activeTab === 'security' && <ShieldCheck className="w-5 h-5" />}
              {activeTab === 'compliance' && <FileCheck className="w-5 h-5" />}
              {activeTab === 'api' && <Code2 className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="text-base font-bold text-[#011405] tracking-tight">
                {activeTab === 'security' && 'Security & Cryptographic Architecture'}
                {activeTab === 'compliance' && 'Forensic Admissibility & Standards'}
                {activeTab === 'api' && 'REST API & Ingest Endpoint Specs'}
              </h3>
              <p className="text-xs text-[#55785d]">
                TraceX Forensics Specification Standard v3.4
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-[#011405] rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="px-6 py-2.5 bg-[#f7fef8] border-b border-[#e3f6e6] flex gap-2">
          {(['security', 'compliance', 'api'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                activeTab === tab
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-[#2d4a34] hover:text-[#011405] hover:bg-slate-200/60'
              }`}
            >
              {tab === 'security' ? 'Security Model' : tab === 'compliance' ? 'Compliance' : 'API Specs'}
            </button>
          ))}
        </div>

        {/* Tab Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs text-[#011405]">
          {activeTab === 'security' && (
            <div className="space-y-3">
              <div className="bg-[#f7fef8] p-4 rounded-xl border border-[#d2ecd6] space-y-1.5">
                <h4 className="font-bold text-[#011405] text-sm flex items-center gap-1.5">
                  <Lock className="w-4 h-4 text-[#415ef4]" />
                  SHA-256 Bit-Level WORM Ingestion
                </h4>
                <p className="text-[#2d4a34] leading-relaxed">
                  Before video demuxing or CV inference begins, raw binary bitstreams are sealed using NIST FIPS 180-4 compliant SHA-256 hashing. Original evidence is isolated in write-once-read-many (WORM) read-only storage (mode 0444).
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-4 rounded-xl bg-[#f7fef8] border border-[#d2ecd6]">
                  <div className="font-bold text-[#011405] mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#16d639]" />
                    Dual Cryptographic Hashing
                  </div>
                  <p className="text-[#2d4a34] leading-relaxed">
                    Calculates dual SHA-256 and MD5 hashes upon initial disk image acquisition for cross-jurisdiction validation.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#f7fef8] border border-[#d2ecd6]">
                  <div className="font-bold text-[#011405] mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#16d639]" />
                    Cryptographic Provenance
                  </div>
                  <p className="text-[#2d4a34] leading-relaxed">
                    Every transcode pass, parser output, and detected event is signed with an immutable timestamp ledger.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'compliance' && (
            <div className="space-y-3">
              <div className="bg-[#f7fef8] p-4 rounded-xl border border-[#d2ecd6]">
                <h4 className="font-bold text-[#011405] text-sm mb-1">ISO/IEC 27037:2012 Certified Architecture</h4>
                <p className="text-[#2d4a34] leading-relaxed">
                  Guidelines for identification, collection, acquisition, and preservation of digital evidence guaranteeing strict courtroom admissibility.
                </p>
              </div>

              <ul className="space-y-2">
                <li className="p-3 rounded-xl bg-[#f7fef8] border border-[#d2ecd6] flex items-center justify-between">
                  <span className="font-medium text-[#011405]">NIST SP 800-86 (Forensic Techniques Integration)</span>
                  <span className="text-[#011405] font-bold bg-[#e6faea] px-2 py-0.5 rounded border border-[#bde3c3]">100% COMPLIANT</span>
                </li>
                <li className="p-3 rounded-xl bg-[#f7fef8] border border-[#d2ecd6] flex items-center justify-between">
                  <span className="font-medium text-[#011405]">CJIS Security Policy v5.9 (Law Enforcement Standard)</span>
                  <span className="text-[#011405] font-bold bg-[#e6faea] px-2 py-0.5 rounded border border-[#bde3c3]">AUTHORIZED</span>
                </li>
                <li className="p-3 rounded-xl bg-[#f7fef8] border border-[#d2ecd6] flex items-center justify-between">
                  <span className="font-medium text-[#011405]">Federal Rules of Evidence Rule 901 & 902</span>
                  <span className="text-[#011405] font-bold bg-[#e6faea] px-2 py-0.5 rounded border border-[#bde3c3]">AUDITED</span>
                </li>
              </ul>
            </div>
          )}

          {activeTab === 'api' && (
            <div className="space-y-3 font-mono">
              <div className="flex items-center justify-between text-[#55785d] font-sans">
                <span className="text-xs font-semibold">Ingest Endpoint Specification (cURL):</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(sampleApiCall);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="flex items-center gap-1 text-[#415ef4] hover:text-indigo-800 font-semibold cursor-pointer transition-colors text-xs"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-[#16d639]" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy cURL'}</span>
                </button>
              </div>

              <pre className="bg-slate-900 text-indigo-300 p-4 rounded-xl text-xs overflow-x-auto leading-relaxed border border-slate-800">
                {sampleApiCall}
              </pre>

              <div className="text-xs text-[#55785d] space-y-1 pt-1 font-sans">
                <p>• Response: <code className="text-[#011405] font-semibold bg-slate-100 px-1.5 py-0.5 rounded">200 OK</code> with JSON payload containing events, timeline, and integrity diagnostics.</p>
                <p>• Endpoints: <code className="text-[#415ef4]">/cases</code>, <code className="text-[#415ef4]">/evidence</code>, <code className="text-[#415ef4]">/video/analyze</code>, <code className="text-[#415ef4]">/video/query</code></p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-[#f7fef8] border-t border-[#e3f6e6] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white border border-[#d2ecd6] rounded-lg text-xs font-medium text-[#011405] hover:bg-slate-100 cursor-pointer shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
