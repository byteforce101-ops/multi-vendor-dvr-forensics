import React, { useState } from 'react';
import { Menu, User, ShieldCheck, LogOut, Key } from 'lucide-react';
import { SupabaseUser } from '../types';
import { TraceXLogo } from './TraceXLogo';

interface HeaderProps {
  user: SupabaseUser;
  onNavChange: (nav: string) => void;
  onOpenAuth: () => void;
  onOpenActivityLog: () => void;
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
  onNavigateToArchitecture?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  onNavChange,
  onOpenAuth,
  onOpenActivityLog,
  onToggleSidebar,
  sidebarOpen,
  onNavigateToArchitecture,
}) => {
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  return (
    <header className="w-full bg-[#f4eee3]/95 border-b border-[#e2d8ca] sticky top-0 z-30 backdrop-blur-md transition-colors">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Sidebar Toggle & Brand */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          <button
            id="nav-hamburger-btn"
            onClick={onToggleSidebar}
            className="p-2 rounded-xl text-[#221e1b] hover:bg-[#eae2d5] border border-[#ded4c5] transition-all cursor-pointer focus:outline-none"
            aria-label="Toggle sidebar menu"
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <Menu className="w-5 h-5 stroke-[2.2]" />
          </button>

          {/* TraceX Logo - Clicks navigate to Architecture overview */}
          <div
            onClick={() => {
              if (onNavigateToArchitecture) {
                onNavigateToArchitecture();
              } else {
                onNavChange('Pipelines');
              }
            }}
            className="flex items-center space-x-2.5 cursor-pointer group"
            title="TraceX - Click to view Architecture & Platform Capabilities"
          >
            <TraceXLogo size={32} variant="gold" bgColor="#0f1715" />
            <span className="text-[19px] font-extrabold tracking-tight text-[#221e1b] font-['DM_Sans',sans-serif] group-hover:text-[#1b4e39] transition-colors">
              TraceX
            </span>
          </div>
        </div>

        {/* Right: User Profile (single entry point for auth + activity log) */}
        <div className="flex items-center space-x-3">
          <div className="relative">
            <button
              id="user-profile-btn"
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center space-x-2.5 text-right group py-1 px-2 rounded-xl hover:bg-[#eae2d5] transition-colors border border-transparent hover:border-[#ded5c7] cursor-pointer"
            >
              <div className="hidden sm:block leading-tight text-right">
                <div className="text-[13px] font-semibold text-[#221e1b] tracking-tight">
                  {user.name}
                </div>
                <div className="text-[11px] font-mono text-[#635b52]">
                  {user.enterpriseId}
                </div>
              </div>

              <div className="w-8 h-8 rounded-xl bg-[#0f2338] text-white flex items-center justify-center text-xs font-semibold shadow-xs relative">
                <User className="w-4 h-4" />
                <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-[#5e7d6f] border-2 border-[#f4eee3] rounded-full"></span>
              </div>
            </button>

            {userDropdownOpen && (
              <div
                className="absolute right-0 mt-2 w-64 bg-[#fcfbf8] rounded-2xl shadow-xl border border-[#e4ded4] py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150"
                onClick={() => setUserDropdownOpen(false)}
              >
                <div className="px-4 py-2.5 border-b border-[#ede5d8]">
                  <p className="text-xs font-bold text-[#221e1b]">{user.name}</p>
                  <p className="text-xs text-[#635b52] truncate">{user.email}</p>
                </div>

                <button
                  onClick={onOpenAuth}
                  className="w-full text-left px-4 py-2 text-xs text-[#221e1b] hover:bg-[#f5efe4] flex items-center gap-2 cursor-pointer"
                >
                  <Key className="w-3.5 h-3.5 text-[#0f2338]" />
                  <span>Profile & Session</span>
                </button>

                <button
                  onClick={onOpenActivityLog}
                  className="w-full text-left px-4 py-2 text-xs text-[#221e1b] hover:bg-[#f5efe4] flex items-center gap-2 cursor-pointer"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-[#3b5749]" />
                  <span>Activity Log</span>
                </button>

                <div className="border-t border-[#ede5d8] my-1"></div>

                <button
                  onClick={onOpenAuth}
                  className="w-full text-left px-4 py-2 text-xs text-[#c2593f] hover:bg-rose-50 flex items-center gap-2 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5 text-[#c2593f]" />
                  <span>Sign out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};