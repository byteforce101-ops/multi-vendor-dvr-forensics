import React from 'react';
import { X, ShieldCheck, LogOut, Mail } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { SupabaseUser } from '../types';

interface SupabaseAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: SupabaseUser;
}

export const SupabaseAuthModal: React.FC<SupabaseAuthModalProps> = ({ isOpen, onClose, currentUser }) => {
  if (!isOpen) return null;

  const handleSignOut = async () => {
    if (supabase) await supabase.auth.signOut();
    onClose();
    // App.tsx's onAuthStateChange listener picks up the sign-out and
    // swaps back to <AuthGate /> automatically.
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1e1b18]/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#fcfbf8] rounded-2xl max-w-md w-full border border-[#e6ded2] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="px-6 py-5 border-b border-[#e6ded2] flex items-center justify-between bg-[#f5efe4]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-[17px] font-semibold text-[#221e1b] font-['DM_Sans',sans-serif]">
                Session
              </h3>
              <p className="text-xs text-[#6e6459] font-mono">Supabase Authentication</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#8c8275] hover:text-[#221e1b] rounded-lg hover:bg-black/5 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 text-sm">
          <div className="flex items-center gap-2 text-[#221e1b]">
            <Mail className="w-4 h-4 text-[#3b5749]" />
            <span className="font-medium">{currentUser.email}</span>
          </div>
          <div className="text-xs text-[#6e6459] font-mono break-all">User ID: {currentUser.id}</div>

          <button
            onClick={handleSignOut}
            className="w-full mt-4 px-4 py-2.5 rounded-xl text-[#c2593f] font-semibold border border-[#e6ded2] hover:bg-rose-50 flex items-center justify-center gap-2 cursor-pointer transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </div>
  );
};