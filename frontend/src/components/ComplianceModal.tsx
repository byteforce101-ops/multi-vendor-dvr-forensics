import React, { useState } from 'react';
import { X, ShieldCheck, FileCheck, Code2, Lock, Terminal, CheckCircle2, Copy, Check } from 'lucide-react';

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

  const sampleApiCall = `curl -X POST https://api.visionstream.ai/v1/evidence/ingest \\
  -H "Authorization: Bearer sb-jwt-eyJhbGciOiJIUzI1NiIsIn..." \\
  -H "X-Enterprise-ID: 10D11A8" \\
  -F "case_id=V-2024-081A" \\
  -F "file=@Interrogation_RM3_A.mp4"`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1e1b18]/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#fcfbf8] rounded-2xl max-w-3xl w-full border border-[#e6ded2] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-[#e6ded2] flex items-center justify-between bg-[#f5efe4]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center">
              {activeTab === 'security' && <ShieldCheck className="w-5 h-5" />}
              {activeTab === 'compliance' && <FileCheck className="w-5 h-5" />}
              {activeTab === 'api' && <Code2 className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="text-[19px] font-semibold text-[#221e1b] font-['DM_Sans',sans-serif]">
                {activeTab === 'security' && 'Security & Cryptographic Guarantees'}
                {activeTab === 'compliance' && 'Forensic Compliance & Certifications'}
                {activeTab === 'api' && 'Enterprise REST & Ingestion API Docs'}
              </h3>
              <p className="text-xs text-[#6e6459] font-mono">
                TraceX Enterprise Specification Standard v3.4
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

        {/* Tab Selector */}
        <div className="px-6 py-2.5 bg-[#f5efe4] border-b border-[#e6ded2] flex gap-2">
          {(['security', 'compliance', 'api'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors cursor-pointer ${
                activeTab === tab
                  ? 'bg-white text-[#0f2338] shadow-xs border border-[#ded5c7]'
                  : 'text-[#6e6459] hover:text-[#221e1b] hover:bg-white/50'
              }`}
            >
              {tab === 'security' ? 'Security Model' : tab === 'compliance' ? 'Compliance' : 'API Docs'}
            </button>
          ))}
        </div>

        {/* Tab Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs font-['DM_Sans',sans-serif]">
          {activeTab === 'security' && (
            <div className="space-y-4">
              <div className="bg-[#eaf1ed] p-4 rounded-xl border border-[#c9dcd0]">
                <h4 className="font-bold text-[#221e1b] text-sm mb-1">SHA-256 Bit-Level Ingestion</h4>
                <p className="text-[#2b4d3a] leading-relaxed">
                  Before video demuxing or inference begins, raw binary streams are sealed using NIST FIPS 180-4 compliant SHA-256 hashing. The original bitstream is written to write-once-read-many (WORM) immutable cold storage.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl border border-[#e6ded2] bg-white">
                  <div className="font-bold text-[#221e1b] mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#3b5749]" />
                    TLS 1.3 & AES-256-GCM
                  </div>
                  <p className="text-[#6e6459]">
                    End-to-end encryption in transit and at rest with hardware-backed HSM keys.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-[#e6ded2] bg-white">
                  <div className="font-bold text-[#221e1b] mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#3b5749]" />
                    Cryptographic Provenance
                  </div>
                  <p className="text-[#6e6459]">
                    Every modification, transcoder step, and AI detection event is signed with an immutable timestamp ledger.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'compliance' && (
            <div className="space-y-4">
              <div className="bg-[#eaf1ed] p-4 rounded-xl border border-[#c9dcd0]">
                <h4 className="font-bold text-[#221e1b] text-sm mb-1">ISO/IEC 27037:2012 Certified</h4>
                <p className="text-[#2b4d3a] leading-relaxed">
                  Guidelines for identification, collection, acquisition, and preservation of digital evidence to guarantee courtroom admissibility.
                </p>
              </div>

              <ul className="space-y-2.5 font-mono">
                <li className="p-3 rounded-xl border border-[#e6ded2] bg-[#f5efe4] flex items-center justify-between text-[#221e1b]">
                  <span>CJIS Security Policy v5.9 (FBI Standard)</span>
                  <span className="text-[#2b4d3a] font-bold">100% Compliant</span>
                </li>
                <li className="p-3 rounded-xl border border-[#e6ded2] bg-[#f5efe4] flex items-center justify-between text-[#221e1b]">
                  <span>FedRAMP High Baseline (GovCloud)</span>
                  <span className="text-[#2b4d3a] font-bold">Authorized</span>
                </li>
                <li className="p-3 rounded-xl border border-[#e6ded2] bg-[#f5efe4] flex items-center justify-between text-[#221e1b]">
                  <span>SOC 2 Type II (Security, Availability, Integrity)</span>
                  <span className="text-[#2b4d3a] font-bold">Audited</span>
                </li>
              </ul>
            </div>
          )}

          {activeTab === 'api' && (
            <div className="space-y-4 font-mono">
              <div className="flex items-center justify-between text-[#6e6459]">
                <span>Ingest Endpoint Specification (cURL):</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(sampleApiCall);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="flex items-center gap-1 text-[#0f2338] hover:text-[#c2593f] font-bold cursor-pointer transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-[#3b5749]" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy cURL'}</span>
                </button>
              </div>

              <pre className="bg-[#141b22] text-[#c9dcd0] p-4 rounded-xl text-xs overflow-x-auto leading-relaxed border border-[#232f3d]">
                {sampleApiCall}
              </pre>

              <div className="text-[11px] text-[#6e6459] space-y-1">
                <p>• Response: <code className="text-[#0f2338] font-bold bg-[#eaf1ed] px-1 py-0.5 rounded">201 Created</code> with SHA-256 signature payload.</p>
                <p>• Webhooks: <code className="text-[#3b5749]">evidence.hashed</code>, <code className="text-[#3b5749]">analysis.completed</code>.</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[#f5efe4] border-t border-[#e6ded2] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white border border-[#ded5c7] rounded-lg text-xs font-semibold text-[#221e1b] hover:bg-black/5 cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
