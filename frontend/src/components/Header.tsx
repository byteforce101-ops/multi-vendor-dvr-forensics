import React, { useState } from 'react';
import { Menu, User, ShieldCheck, LogOut, Key, ChevronDown } from 'lucide-react';
import { SupabaseUser } from '../types';

interface HeaderProps {
  user: SupabaseUser;
  onNavChange: (nav: string) => void;
  onOpenAuth: () => void;
  onOpenActivityLog: () => void;
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  onNavChange,
  onOpenAuth,
  onOpenActivityLog,
  onToggleSidebar,
  sidebarOpen,
}) => {
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  return (
    <header className="w-full sticky top-0 z-30 backdrop-blur-md transition-colors bg-white/85 border-b border-slate-200/80 shadow-xs">
      <div className="max-w-[1550px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Left: Sidebar Toggle & Logo */}
        <div className="flex items-center gap-3">
          <button
            id="nav-hamburger-btn"
            onClick={onToggleSidebar}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-200 bg-slate-50/80 text-slate-700 hover:text-slate-900 hover:bg-slate-100 hover:border-slate-300 transition-all cursor-pointer shadow-xs active:scale-95"
            aria-label="Toggle sidebar menu"
            title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            <Menu className="w-4 h-4" />
          </button>

          <div
            onClick={() => onNavChange('Pipelines')}
            className="flex items-center gap-2.5 cursor-pointer select-none group"
          >
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-xs group-hover:bg-indigo-700 transition-colors">
              <span>TX</span>
            </div>
            <div>
              <span className="text-[15px] font-bold tracking-tight text-slate-900 leading-none block">
                TraceX
              </span>
              <span className="text-[10px] text-slate-500 font-medium tracking-wide block mt-0.5">
                Forensics Studio
              </span>
            </div>
          </div>
        </div>

        {/* Right: Quick Action Buttons & User Profile */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onOpenActivityLog}
            className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100/90 border border-slate-200/80 transition-all cursor-pointer shadow-xs active:scale-98"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Chain of Custody</span>
          </button>

          <div className="relative">
            <button
              id="user-profile-btn"
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2 py-1.5 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-900 transition-all cursor-pointer shadow-xs active:scale-98"
            >
              <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200 flex items-center justify-center font-bold text-xs">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="hidden sm:block text-left text-xs font-semibold text-slate-800 leading-tight">
                {user.name}
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {userDropdownOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white/95 backdrop-blur-xl border border-slate-200/90 rounded-xl shadow-xl shadow-slate-900/5 py-1 z-50 text-xs animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3.5 py-2 border-b border-slate-100">
                  <p className="font-semibold text-slate-900 truncate">{user.name}</p>
                  <p className="text-slate-500 text-[11px] truncate">{user.email || 'Examiner'}</p>
                </div>

                <button
                  onClick={() => {
                    setUserDropdownOpen(false);
                    onOpenAuth();
                  }}
                  className="w-full text-left px-3.5 py-2 text-slate-700 hover:text-slate-900 hover:bg-slate-50 flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  <span>Account Session</span>
                </button>

                <button
                  onClick={() => {
                    setUserDropdownOpen(false);
                    onOpenActivityLog();
                  }}
                  className="w-full text-left px-3.5 py-2 text-slate-700 hover:text-slate-900 hover:bg-slate-50 flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Chain of Custody</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};