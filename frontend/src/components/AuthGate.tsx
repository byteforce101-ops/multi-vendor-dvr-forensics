import React, { useState } from 'react';
import { Mail, Lock, Loader2 } from 'lucide-react';
import { supabase, isSupabaseConfigured } from '../lib/supabase';
import { TraceXLogo } from './TraceXLogo';

interface AuthGateProps {
  onAuthenticated: () => void;
}

export const AuthGate: React.FC<AuthGateProps> = ({ onAuthenticated }) => {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!isSupabaseConfigured || !supabase) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f4eee3] p-6">
        <div className="max-w-md text-center bg-[#fcfbf8] border border-[#e6ded2] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-[#221e1b]">Supabase is not configured</h2>
          <p className="text-sm text-[#6e6459] mt-2">
            Set <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> in
            <code> frontend/.env.local</code>, then restart the dev server.
          </p>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!supabase) return; // add this line

  setError(null);
  setInfo(null);
  setBusy(true);
  try {
    if (mode === 'signin') {
      const { error: err } = await supabase.auth.signInWithPassword({ email, password });
      if (err) throw err;
      onAuthenticated();
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
    <div className="min-h-screen flex items-center justify-center bg-[#f4eee3] p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-[#fcfbf8] border border-[#e6ded2] rounded-2xl p-8 shadow-[0_4px_20px_-4px_rgba(34,30,27,0.08)]"
      >
        <div className="flex items-center gap-2.5 mb-6">
          <TraceXLogo size={32} variant="gold" bgColor="#0f1715" />
          <span className="text-lg font-bold text-[#221e1b]">TraceX</span>
        </div>

        <h1 className="text-xl font-semibold text-[#221e1b]">
          {mode === 'signin' ? 'Sign in' : 'Create account'}
        </h1>
        <p className="text-xs text-[#6e6459] mt-1 mb-5 font-mono">
          Supabase-authenticated forensic session
        </p>

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
          onClick={() => {
            setMode(mode === 'signin' ? 'signup' : 'signin');
            setError(null);
            setInfo(null);
          }}
          className="w-full text-center text-xs text-[#0f2338] mt-4 hover:underline cursor-pointer"
        >
          {mode === 'signin' ? 'Need an account? Sign up' : 'Have an account? Sign in'}
        </button>
      </form>
    </div>
  );
};