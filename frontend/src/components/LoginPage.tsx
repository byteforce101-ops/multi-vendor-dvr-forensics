import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Lock,
  Mail,
  User,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  Sparkles,
  Terminal,
  Activity,
  ChevronRight,
  Loader2,
  HardDrive,
  Cpu,
  FileCheck2,
} from 'lucide-react';
import { supabase, isSupabaseConfigured, DEFAULT_USER } from '../lib/supabase';
import { SupabaseUser } from '../types';
import TraceXLogo from './TraceXLogo';

interface LoginPageProps {
  onLoginSuccess: (user: SupabaseUser) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [badgeId, setBadgeId] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Clear messages on mode switch
  useEffect(() => {
    setError(null);
    setSuccessMessage(null);
  }, [mode]);

  const extractNameFromEmail = (mailStr: string) => {
    const local = mailStr.split('@')[0] || 'Examiner';
    return local
      .replace(/[._-]/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!email || !password) {
      setError('Please provide both examiner email and access credentials.');
      return;
    }

    if (password.length < 6) {
      setError('Access password must be at least 6 characters.');
      return;
    }

    setLoading(true);

    try {
      if (isSupabaseConfigured && supabase) {
        if (mode === 'signin') {
          const { data, error: authError } = await supabase.auth.signInWithPassword({
            email: email.trim(),
            password,
          });

          if (authError) throw authError;

          if (data.user) {
            const userName =
              data.user.user_metadata?.full_name ||
              data.user.user_metadata?.name ||
              extractNameFromEmail(data.user.email || email);

            const authedUser: SupabaseUser = {
              id: data.user.id,
              email: data.user.email || email,
              role: data.user.user_metadata?.role || 'Senior Forensic Analyst',
              enterpriseId: data.user.user_metadata?.badge_id || 'TRACEX-AUTH',
              name: userName,
              isLoggedIn: true,
            };

            onLoginSuccess(authedUser);
          }
        } else {
          // Sign up
          const { data, error: signUpErr } = await supabase.auth.signUp({
            email: email.trim(),
            password,
            options: {
              data: {
                full_name: fullName.trim() || extractNameFromEmail(email),
                badge_id: badgeId.trim() || `FX-${Math.floor(1000 + Math.random() * 9000)}`,
                role: 'Senior Forensic Analyst',
              },
            },
          });

          if (signUpErr) throw signUpErr;

          if (data.session && data.user) {
            // Immediate session
            const userName =
              data.user.user_metadata?.full_name || fullName.trim() || extractNameFromEmail(email);

            onLoginSuccess({
              id: data.user.id,
              email: data.user.email || email,
              role: 'Senior Forensic Analyst',
              enterpriseId: badgeId.trim() || 'TRACEX-AUTH',
              name: userName,
              isLoggedIn: true,
            });
          } else {
            // Email confirmation required
            setSuccessMessage(
              'Examiner account created successfully. Check your email inbox to verify your credentials, or proceed to sign in.'
            );
            setMode('signin');
          }
        }
      } else {
        // Local workstation offline mode fallback
        await new Promise((r) => setTimeout(r, 450));
        const localUser: SupabaseUser = {
          id: `local_usr_${Date.now().toString(36)}`,
          email: email.trim(),
          role: 'Senior Forensic Analyst',
          enterpriseId: badgeId.trim() || 'LOCAL-STATION-01',
          name: fullName.trim() || extractNameFromEmail(email),
          isLoggedIn: true,
        };
        onLoginSuccess(localUser);
      }
    } catch (err: any) {
      console.error('Authentication error:', err);
      setError(err?.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleBypassOrGuest = () => {
    onLoginSuccess({
      ...DEFAULT_USER,
      name: 'Lead Forensic Investigator',
      isLoggedIn: true,
    });
  };

  return (
    <div className="min-h-screen w-full flex bg-[#f5f6f7] text-[#111827] font-sans antialiased selection:bg-[#c7d2fe] selection:text-[#172554]">
      {/* LEFT COLUMN: Forensic Branding & Platform Capabilities Hero */}
      <div className="hidden lg:flex lg:w-[48%] xl:w-[52%] bg-[#172554] text-white flex-col justify-between p-12 relative overflow-hidden">
        {/* Subtle grid and ambient lighting overlays */}
        <div
          className="absolute inset-0 pointer-events-none opacity-10"
          style={{
            backgroundImage:
              'linear-gradient(#5eead4 1px, transparent 1px), linear-gradient(90deg, #5eead4 1px, transparent 1px)',
            backgroundSize: '36px 36px',
          }}
        />
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-[#2dd4bf]/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-[#3730a3]/40 rounded-full blur-3xl pointer-events-none" />

        {/* Top Header */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <TraceXLogo variant="white" className="h-12 w-auto object-contain" />
          </div>
        </div>

        {/* Middle Hero Showcase */}
        <div className="relative z-10 my-auto py-8 max-w-xl">
          <h1 className="text-3xl xl:text-4xl font-semibold tracking-tight text-white leading-[1.2] mb-4">
            Cryptographic Integrity & Neural Event Reconstruction.
          </h1>

          <p className="text-slate-300 text-sm xl:text-base leading-relaxed mb-8">
            Acquire multi-channel DVR raw disk sectors, verify SHA-256 bitstream continuity, and perform temporal kinematic event reconstruction with zero data loss.
          </p>

          {/* Feature Highlights Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="w-8 h-8 rounded-md bg-[#0f766e]/30 text-[#5eead4] flex items-center justify-center mb-2.5">
                <HardDrive className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-semibold text-white mb-1">DVR File System Carving</h4>
              <p className="text-[11px] text-slate-300 leading-normal">
                DHFS, WFS, and raw sector recovery with H.264/H.265 GOP parsing.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="w-8 h-8 rounded-md bg-[#3730a3]/40 text-[#c7d2fe] flex items-center justify-center mb-2.5">
                <Cpu className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-semibold text-white mb-1">OpenCV Rule Engine</h4>
              <p className="text-[11px] text-slate-300 leading-normal">
                Multi-stage kinematic velocity tracking, HOG pedestrian & Haar cascades.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="w-8 h-8 rounded-md bg-[#047857]/40 text-[#a7f3d0] flex items-center justify-center mb-2.5">
                <FileCheck2 className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-semibold text-white mb-1">Tamper Audit & Dossiers</h4>
              <p className="text-[11px] text-slate-300 leading-normal">
                Continuous frame timestamp audits & certified NIST court reporting.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="w-8 h-8 rounded-md bg-[#7c3aed]/40 text-[#ddd6fe] flex items-center justify-center mb-2.5">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-semibold text-white mb-1">Supabase Access Control</h4>
              <p className="text-[11px] text-slate-300 leading-normal">
                Role-based audit logging and encrypted evidence repository ledger.
              </p>
            </div>
          </div>
        </div>

        {/* Footer Meta */}
        <div className="relative z-10 pt-6 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span className="flex items-center gap-1 text-[#5eead4]">
            <Terminal className="w-3.5 h-3.5" />
            SYSTEM READY
          </span>
        </div>
      </div>

      {/* RIGHT COLUMN: Authentication Form */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12 lg:p-16 relative">
        {/* Mobile Logo banner */}
        <div className="lg:hidden mb-8 text-center flex flex-col items-center">
          <TraceXLogo variant="dark" className="h-11 w-auto object-contain mb-2" />
          <p className="text-xs text-slate-500 font-medium">Digital Video Forensics & Integrity Platform</p>
        </div>

        <div className="w-full max-w-md bg-white border border-[#e2e6ea] rounded-xl shadow-xl shadow-slate-900/5 p-8 sm:p-10">
          {/* Header */}
          <div className="mb-6 text-left">
            <div className="mb-2">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#64748b]">
                {mode === 'signin' ? 'AUTHENTICATION GATEWAY' : 'NEW EXAMINER ONBOARDING'}
              </span>
            </div>

            <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
              {mode === 'signin' ? 'Sign in to Trace-X' : 'Register Examiner Identity'}
            </h2>
            <p className="text-xs text-[#64748b] mt-1.5 leading-relaxed">
              {mode === 'signin'
                ? 'Authenticate to access active investigations, evidence vaults, and AI forensic analysis.'
                : 'Create credentials to access verified evidence workflows and tamper audit trails.'}
            </p>
          </div>

          {/* Tab Switcher */}
          <div className="flex bg-[#f0f2f4] p-1 rounded-lg mb-6 border border-[#e2e6ea]">
            <button
              type="button"
              onClick={() => setMode('signin')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                mode === 'signin'
                  ? 'bg-white text-[#172554] shadow-xs'
                  : 'text-[#64748b] hover:text-[#172033]'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setMode('signup')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                mode === 'signup'
                  ? 'bg-white text-[#172554] shadow-xs'
                  : 'text-[#64748b] hover:text-[#172033]'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Feedback Alerts */}
          {error && (
            <div className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5 animate-in fade-in duration-150">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
              <div className="flex-1 font-medium">{error}</div>
            </div>
          )}

          {successMessage && (
            <div className="mb-5 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-start gap-2.5 animate-in fade-in duration-150">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
              <div className="flex-1 font-medium">{successMessage}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleAuthSubmit} className="space-y-4">
            {mode === 'signup' && (
              <>
                <div>
                  <label className="block text-xs font-semibold text-[#334155] mb-1.5">
                    Examiner Full Name *
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-[#94a3b8] absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      required
                      placeholder="Special Agent Alex Morgan"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-[#cbd5e1] rounded-md text-[#1e293b] placeholder:text-[#94a3b8] focus:outline-none focus:border-[#0891b2] focus:ring-2 focus:ring-[#0891b2]/15 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#334155] mb-1.5">
                    Badge / Unit Identifier
                  </label>
                  <div className="relative">
                    <ShieldCheck className="w-4 h-4 text-[#94a3b8] absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="e.g. FX-9842 / Cyber Crime Unit"
                      value={badgeId}
                      onChange={(e) => setBadgeId(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-[#cbd5e1] rounded-md text-[#1e293b] placeholder:text-[#94a3b8] focus:outline-none focus:border-[#0891b2] focus:ring-2 focus:ring-[#0891b2]/15 transition"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-semibold text-[#334155] mb-1.5">
                Examiner Email Address *
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#94a3b8] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  placeholder="investigator@agency.gov"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-[#cbd5e1] rounded-md text-[#1e293b] placeholder:text-[#94a3b8] focus:outline-none focus:border-[#0891b2] focus:ring-2 focus:ring-[#0891b2]/15 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#334155] mb-1.5">
                Access Password *
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#94a3b8] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={6}
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-10 py-2 text-xs bg-white border border-[#cbd5e1] rounded-md text-[#1e293b] placeholder:text-[#94a3b8] focus:outline-none focus:border-[#0891b2] focus:ring-2 focus:ring-[#0891b2]/15 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94a3b8] hover:text-[#334155] transition"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 rounded-md text-xs font-semibold text-white bg-gradient-to-r from-[#172554] to-[#3730a3] hover:from-[#1e3a8a] hover:to-[#4338ca] shadow-md shadow-indigo-950/15 flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>{mode === 'signin' ? 'Access Forensic Workspace' : 'Create & Verify Account'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Local Guest / Quick Workstation Access */}
          <div className="mt-6 pt-5 border-t border-[#e2e6ea] text-center">
            <button
              type="button"
              onClick={handleBypassOrGuest}
              className="text-xs font-semibold text-[#172554] hover:text-[#0f766e] flex items-center justify-center gap-1.5 mx-auto transition cursor-pointer"
            >
              <span>Continue as Local Workstation Analyst</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <p className="text-[10px] text-[#94a3b8] mt-1.5">
              No cloud login required for offline evidence analysis & NIST report generation.
            </p>
          </div>
        </div>

        {/* Legal / Compliance Notice */}
        <p className="text-[11px] text-slate-400 mt-8 text-center max-w-sm">
          Trace-X ensures bitstream isolation and strict cryptographic custody compliance for all uploaded media.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
