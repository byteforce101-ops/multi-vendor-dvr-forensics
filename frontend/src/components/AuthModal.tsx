import React, { useState } from 'react';
import { X, ShieldCheck, LogOut, Mail, Lock, Loader2 } from 'lucide-react';
import { supabase, isSupabaseConfigured } from '../lib/supabase';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  isAuthenticated: boolean;
  userEmail?: string;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, isAuthenticated, userEmail }) => {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!isOpen) return null;

  const handleSignOut = async () => {
    if (supabase) await supabase.auth.signOut();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) return;
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      if (mode === 'signin') {
        const { error: err } = await supabase.auth.signInWithPassword({ email, password });
        if (err) throw err;
        onClose();
      } else {
        const { error: err } = await supabase.auth.signUp({ email, password });
        if (err) throw err;
        setInfo('Account created. Check your email to confirm it, then sign in.');
        setMode('signin');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1e1b18]/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-[#fcfbf8] rounded-2xl max-w-sm w-full border border-[#e6ded2] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="px-6 py-5 border-b border-[#e6ded2] flex items-center justify-between bg-[#f5efe4]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#eaf1ed] text-[#3b5749] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-[17px] font-semibold text-[#221e1b]">
              {isAuthenticated ? 'Session' : 'Sign in'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1.5 text-[#8c8275] hover:text-[#221e1b] rounded-lg hover:bg-black/5 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {!isSupabaseConfigured ? (
          <div className="p-6 text-sm text-[#6e6459]">
            Supabase isn't configured. Set <code>VITE_SUPABASE_URL</code> and{' '}
            <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> in <code>frontend/.env.local</code>.
          </div>
        ) : isAuthenticated ? (
          <div className="p-6 space-y-4 text-sm">
            <div className="flex items-center gap-2 text-[#221e1b]">
              <Mail className="w-4 h-4 text-[#3b5749]" />
              <span className="font-medium">{userEmail}</span>
            </div>
            <button
              onClick={handleSignOut}
              className="w-full mt-2 px-4 py-2.5 rounded-xl text-[#c2593f] font-semibold border border-[#e6ded2] hover:bg-rose-50 flex items-center justify-center gap-2 cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign out</span>
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6">
            <label className="block text-xs font-bold text-[#221e1b] mb-1 uppercase tracking-wide">Email</label>
            <div className="relative mb-4">
              <Mail className="w-4 h-4 text-[#8c8275] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 bg-[#fffdfa] border border-[#dcd4c7] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0f2338]/30"
              />
            </div>

            <label className="block text-xs font-bold text-[#221e1b] mb-1 uppercase tracking-wide">Password</label>
            <div className="relative mb-5">
              <Lock className="w-4 h-4 text-[#8c8275] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 bg-[#fffdfa] border border-[#dcd4c7] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0f2338]/30"
              />
            </div>

            {error && <p className="text-xs text-[#c2593f] mb-3">{error}</p>}
            {info && <p className="text-xs text-[#2b4d3a] mb-3">{info}</p>}

            <button
              type="submit"
              disabled={busy}
              className="btn-primary-navy w-full py-2.5 rounded-xl text-white text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
            >
              {busy && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{mode === 'signin' ? 'Sign in' : 'Sign up'}</span>
            </button>

            <button
              type="button"
              onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(null); setInfo(null); }}
              className="w-full text-center text-xs text-[#0f2338] mt-4 hover:underline cursor-pointer"
            >
              {mode === 'signin' ? 'Need an account? Sign up' : 'Have an account? Sign in'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};