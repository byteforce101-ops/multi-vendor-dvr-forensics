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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-sm w-full border border-slate-200 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-slate-900 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">
              {isAuthenticated ? 'Examiner Session' : 'Sign In to Station'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        {!isSupabaseConfigured ? (
          <div className="p-6 text-xs text-slate-500 leading-relaxed">
            Local workstation mode active (Supabase optional). For multi-user ledger sync, configure <code className="text-indigo-600 font-semibold">VITE_SUPABASE_URL</code> in environment.
          </div>
        ) : isAuthenticated ? (
          <div className="p-6 space-y-4 text-xs">
            <div className="flex items-center gap-2.5 text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200">
              <Mail className="w-4 h-4 text-indigo-600" />
              <span className="font-semibold">{userEmail}</span>
            </div>
            <button
              onClick={handleSignOut}
              className="w-full px-4 py-2 rounded-lg text-rose-600 font-medium border border-rose-200 hover:bg-rose-50 flex items-center justify-center gap-2 cursor-pointer transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign out</span>
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 text-xs space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-slate-900 mb-1">Examiner Email</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-900 mb-1">Access Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white transition-colors"
                />
              </div>
            </div>

            {error && <p className="text-xs text-rose-600 bg-rose-50 p-2 rounded-md border border-rose-200">{error}</p>}
            {info && <p className="text-xs text-emerald-600 bg-emerald-50 p-2 rounded-md border border-emerald-200">{info}</p>}

            <button
              type="submit"
              disabled={busy}
              className="btn-kinetic-primary w-full py-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
            >
              {busy && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{mode === 'signin' ? 'Sign In' : 'Create Account'}</span>
            </button>

            <button
              type="button"
              onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(null); setInfo(null); }}
              className="w-full text-center text-xs text-indigo-600 hover:text-indigo-800 pt-1 cursor-pointer font-medium"
            >
              {mode === 'signin' ? 'Register new examiner credentials' : 'Already registered? Sign in'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
