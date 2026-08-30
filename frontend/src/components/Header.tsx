import React, { useState } from 'react';
import { Menu, User, ShieldCheck, ChevronDown } from 'lucide-react';
import { SupabaseUser } from '../types';
import TraceXLogo from './TraceXLogo';

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

        {/* LEFT: Sidebar Toggle + TraceX Logo */}
        <div className="flex items-center gap-3">

          {/* Sidebar Toggle */}
          <button
            id="nav-hamburger-btn"
            onClick={onToggleSidebar}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-200 bg-slate-50/80 text-slate-700 hover:text-slate-900 hover:bg-slate-100 hover:border-slate-300 transition-all cursor-pointer shadow-xs active:scale-95"
            aria-label="Toggle sidebar menu"
            title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* TraceX Logo */}
          <div
            onClick={() => onNavChange('Pipelines')}
            className="flex items-center cursor-pointer select-none group"
            title="TraceX Forensics Studio"
          >
            <TraceXLogo className="h-9 w-auto group-hover:opacity-90 transition-opacity" />
          </div>
        </div>

        {/* RIGHT: Quick Actions + User Profile */}
        <div className="flex items-center gap-2.5">

          {/* Chain of Custody */}
          <button
            onClick={onOpenActivityLog}
            className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 transition-all cursor-pointer shadow-xs active:scale-98"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>

            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />

            <span>Chain of Custody</span>
          </button>

          {/* User Profile */}
          <div className="relative">
            <button
              id="user-profile-btn"
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2 py-1.5 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-900 transition-all cursor-pointer shadow-xs active:scale-98"
            >
              {/* User Initial */}
              <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-800 border border-blue-200 flex items-center justify-center font-bold text-xs">
                {user.name.charAt(0).toUpperCase()}
              </div>

              {/* User Name */}
              <div className="hidden sm:block text-left text-xs font-semibold text-slate-800 leading-tight">
                {user.name}
              </div>

              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {/* User Dropdown */}
            {userDropdownOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white/95 backdrop-blur-xl border border-slate-200/90 rounded-xl shadow-xl shadow-slate-900/5 py-1 z-50 text-xs animate-in fade-in zoom-in-95 duration-150">

                {/* Account Information */}
                <div className="px-3.5 py-2 border-b border-slate-100">
                  <p className="font-semibold text-slate-900 truncate">
                    {user.name}
                  </p>

                  <p className="text-slate-500 text-[11px] truncate">
                    {user.email || 'Examiner'}
                  </p>
                </div>

                {/* Account Session */}
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

                {/* Chain of Custody */}
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

export default Header;