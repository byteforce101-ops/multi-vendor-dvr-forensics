import React, { useState } from 'react';
import { X, Key, ShieldCheck, Check, AlertCircle, Database, Lock, User, RefreshCw } from 'lucide-react';
import { SupabaseUser } from '../types';
import { isSupabaseConfigured } from '../lib/supabase';

interface SupabaseAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: SupabaseUser;
  onUpdateUser: (user: SupabaseUser) => void;
}

export const SupabaseAuthModal: React.FC<SupabaseAuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onUpdateUser,
}) => {
  const [email, setEmail] = useState(currentUser.email);
  const [role, setRole] = useState(currentUser.role);
  const [enterpriseId, setEnterpriseId] = useState(currentUser.enterpriseId);
  const [isSaved, setIsSaved] = useState(false);

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateUser({
      ...currentUser,
      email,
      role,
      enterpriseId,
      name: email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || 'Enterprise User',
    });
    setIsSaved(true);
    setTimeout(() => {
      setIsSaved(false);
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1e1b18]/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#fcfbf8] rounded-2xl max-w-lg w-full border border-[#e6ded2] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-5 border-b border-[#e6ded2] flex items-center justify-between bg-[#f5efe4]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-[19px] font-semibold text-[#221e1b] font-['EB_Garamond',serif]">
                Supabase Authentication & Identity
              </h3>
              <p className="text-xs text-[#6e6459] font-mono">
                {isSupabaseConfigured ? 'Connected to live Supabase project' : 'Local Enterprise Auth Session'}
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

        {/* Content Form */}
        <form onSubmit={handleSave} className="p-6 space-y-4">
          <div className="p-3.5 bg-[#eaf1ed] rounded-xl border border-[#c9dcd0] text-xs text-[#2b4d3a] leading-relaxed">
            <div className="font-bold flex items-center gap-1.5 mb-1 text-[#221e1b]">
              <ShieldCheck className="w-4 h-4 text-[#3b5749]" />
              Role-Based Access Control (RBAC)
            </div>
            Your authenticated identity will be cryptographically bound into the SHA-256 bitstream ledger for every case created or processed.
          </div>

          <div>
            <label className="block text-xs font-bold text-[#221e1b] mb-1 font-mono uppercase">
              Operator Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-[#fffdfa] border border-[#dcd4c7] rounded-xl text-xs font-mono text-[#221e1b] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/30 focus:border-[#0f2338]"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-[#221e1b] mb-1 font-mono uppercase">
                Enterprise ID
              </label>
              <input
                type="text"
                value={enterpriseId}
                onChange={(e) => setEnterpriseId(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#fffdfa] border border-[#dcd4c7] rounded-xl text-xs font-mono text-[#221e1b] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/30 focus:border-[#0f2338]"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#221e1b] mb-1 font-mono uppercase">
                Assigned Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#fffdfa] border border-[#dcd4c7] rounded-xl text-xs font-mono text-[#221e1b] focus:outline-none focus:ring-2 focus:ring-[#0f2338]/30 focus:border-[#0f2338]"
              >
                <option value="Senior Forensic Analyst">Senior Forensic Analyst</option>
                <option value="Lead Investigator">Lead Investigator</option>
                <option value="Chain-of-Custody Auditor">Chain-of-Custody Auditor</option>
                <option value="System Administrator">System Administrator</option>
              </select>
            </div>
          </div>

          <div className="pt-2">
            <div className="flex items-center justify-between text-xs text-[#6e6459] font-mono py-2 border-t border-[#ede5d8]">
              <span>Token Status:</span>
              <span className="text-[#2b4d3a] font-bold">JWT HS256 Active</span>
            </div>
          </div>

          <div className="pt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-[#5c544c] bg-white border border-[#ded5c7] rounded-lg hover:bg-black/5 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary-navy px-5 py-2 text-xs font-semibold text-white rounded-lg flex items-center gap-1.5 cursor-pointer"
            >
              {isSaved ? <Check className="w-3.5 h-3.5" /> : null}
              <span>{isSaved ? 'Updated Identity' : 'Save Credentials'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
