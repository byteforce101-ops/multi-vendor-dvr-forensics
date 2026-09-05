import React, { useState } from 'react';
import { Chrome, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck, UserRound, X } from 'lucide-react';
import { SupabaseUser } from '../types';
import { isSupabaseConfigured, supabase } from '../lib/supabase';
import TraceXLogo from './TraceXLogo';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthenticated: (user: SupabaseUser) => void;
}

type AuthMode = 'login' | 'signup';

const makeName = (email: string) =>
  email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, (character) => character.toUpperCase()) || 'User';

const makeUser = (id: string, email: string, name?: string): SupabaseUser => ({
  id,
  email,
  role: 'Senior Forensic Analyst',
  enterpriseId: 'LOCAL-USER',
  name: name || makeName(email),
  isLoggedIn: true,
});

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose, onAuthenticated }) => {
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState('');

  if (!isOpen) return null;

  const handleGoogleLogin = async () => {
    setMessage('');
    if (!supabase || !isSupabaseConfigured) {
      setMessage('Google sign-in is not configured yet. Use email and password for local preview.');
      return;
    }

    setIsBusy(true);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    });
    if (error) setMessage(error.message);
    setIsBusy(false);
  };

  const handleEmailAuth = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage('');

    if (mode === 'signup' && password !== confirmPassword) {
      setMessage('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setMessage('Use a password with at least 6 characters.');
      return;
    }

    setIsBusy(true);

    if (supabase && isSupabaseConfigured) {
      const result = mode === 'login'
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });

      if (result.error) {
        setMessage(result.error.message);
        setIsBusy(false);
        return;
      }

      if (mode === 'signup' && !result.data.session) {
        setMessage('Check your email to confirm the new account.');
        setIsBusy(false);
        return;
      }

      if (result.data.user) {
        onAuthenticated(makeUser(result.data.user.id, result.data.user.email || email, result.data.user.user_metadata?.full_name));
        onClose();
      }
    } else {
      await new Promise((resolve) => setTimeout(resolve, 350));
      onAuthenticated(makeUser(`local-${Date.now()}`, email));
      onClose();
    }

    setIsBusy(false);
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#1e1b18]/55 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-sm overflow-hidden rounded-2xl border border-[#e6ded2] bg-[#fcfbf8] shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1.5 text-[#8c8275] transition-colors hover:bg-black/5 hover:text-[#221e1b]"
          aria-label="Close login window"
          title="Close"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="border-b border-[#e6ded2] bg-[#f5efe4] px-6 py-5 pr-14">
          <div className="mb-3">
            <TraceXLogo variant="dark" className="h-7 w-auto object-contain" />
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-[#221e1b]">Sign in to upload</h2>
          <p className="mt-1 text-xs text-[#6e6459]">Protect your evidence before it enters the workspace.</p>
        </div>

        <div className="space-y-4 p-6">
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isBusy}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#dcd4c7] bg-white px-4 py-2.5 text-sm font-semibold text-[#221e1b] transition-colors hover:bg-[#f7f3ed] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Chrome className="h-4 w-4 text-[#4285f4]" />
            Continue with Google
          </button>

          <div className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-widest text-[#a69c90]">
            <span className="h-px flex-1 bg-[#e6ded2]" />
            <span>or</span>
            <span className="h-px flex-1 bg-[#e6ded2]" />
          </div>

          <div className="grid grid-cols-2 rounded-xl bg-[#f5efe4] p-1 text-xs font-semibold">
            <button
              type="button"
              onClick={() => { setMode('login'); setMessage(''); }}
              className={`rounded-lg px-3 py-2 transition-colors ${mode === 'login' ? 'bg-white text-[#0f2338] shadow-sm' : 'text-[#6e6459]'}`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setMessage(''); }}
              className={`rounded-lg px-3 py-2 transition-colors ${mode === 'signup' ? 'bg-white text-[#0f2338] shadow-sm' : 'text-[#6e6459]'}`}
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleEmailAuth} className="space-y-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-[#4a423a]">Email</span>
              <span className="relative block">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8c8275]" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="w-full rounded-xl border border-[#dcd4c7] bg-[#fffdfa] py-2.5 pl-9 pr-3 text-sm text-[#221e1b] outline-none transition focus:border-[#0f2338] focus:ring-2 focus:ring-[#0f2338]/15"
                  required
                />
              </span>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-[#4a423a]">Password</span>
              <span className="relative block">
                <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8c8275]" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-[#dcd4c7] bg-[#fffdfa] py-2.5 pl-9 pr-10 text-sm text-[#221e1b] outline-none transition focus:border-[#0f2338] focus:ring-2 focus:ring-[#0f2338]/15"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8c8275] hover:text-[#221e1b]"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </span>
            </label>

            {mode === 'signup' && (
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-[#4a423a]">Confirm password</span>
                <span className="relative block">
                  <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8c8275]" />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="••••••••"
                    className="w-full rounded-xl border border-[#dcd4c7] bg-[#fffdfa] py-2.5 pl-9 pr-3 text-sm text-[#221e1b] outline-none transition focus:border-[#0f2338] focus:ring-2 focus:ring-[#0f2338]/15"
                    required
                  />
                </span>
              </label>
            )}

            {message && <p className="rounded-lg bg-[#fff3ed] px-3 py-2 text-xs leading-relaxed text-[#a34a32]">{message}</p>}

            <button
              type="submit"
              disabled={isBusy}
              className="btn-primary-navy flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
            >
              {mode === 'login' ? 'Log in' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-[11px] leading-relaxed text-[#8c8275]">
            Google passwords stay with Google. This form only uses your email and password for the configured account service.
          </p>
        </div>
      </div>
    </div>
  );
};