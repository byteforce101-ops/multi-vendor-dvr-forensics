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
    <header className="w-full sticky top-0 z-30 backdrop-blur-md transition-colors bg-white/95 border-b border-[#d2ecd6] shadow-xs">
      <div className="max-w-[1550px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Left: Sidebar Toggle & Logo */}
        <div className="flex items-center gap-3">
          <button
            id="nav-hamburger-btn"
            onClick={onToggleSidebar}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-[#d2ecd6] bg-[#f7fef8] text-[#011405] hover:bg-[#e8f9ec] hover:border-[#bde3c3] transition-all cursor-pointer shadow-xs"
            aria-label="Toggle sidebar menu"
            title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            <Menu className="w-4 h-4" />
          </button>

          <div
            onClick={() => onNavChange('Pipelines')}
            className="flex items-center gap-2.5 cursor-pointer select-none"
          >
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-[#415ef4] to-[#1cf243] flex items-center justify-center text-white font-black text-xs shadow-xs">
              <span>TX</span>
            </div>
            <div>
              <span className="text-[15px] font-bold tracking-tight text-[#011405] leading-none block">
                TraceX
              </span>
              <span className="text-[10px] text-[#2d4a34] font-medium tracking-wide block mt-0.5">
                Forensics Platform
              </span>
            </div>
          </div>
        </div>

        {/* Right: Quick Action Buttons & User Profile */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onOpenActivityLog}
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#011405] hover:bg-[#e8f9ec] bg-[#f7fef8] border border-[#d2ecd6] transition-colors cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-[#16d639]" />
            <span>Chain of Custody</span>
          </button>

          <div className="relative">
            <button
              id="user-profile-btn"
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2 py-1.5 px-2.5 rounded-lg border border-[#d2ecd6] bg-white hover:bg-[#f7fef8] text-[#011405] transition-all cursor-pointer shadow-xs"
            >
              <div className="w-6 h-6 rounded-full bg-[#e8f9ec] text-[#011405] border border-[#d2ecd6] flex items-center justify-center font-bold text-xs">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="hidden sm:block text-left text-xs font-semibold text-[#011405] leading-tight">
                {user.name}
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-[#55785d]" />
            </button>

            {userDropdownOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white border border-[#d2ecd6] rounded-xl shadow-lg py-1 z-50 text-xs animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3.5 py-2 border-b border-[#e3f6e6]">
                  <p className="font-semibold text-[#011405] truncate">{user.name}</p>
                  <p className="text-[#55785d] text-[11px] truncate">{user.email || 'Examiner'}</p>
                </div>

                <button
                  onClick={() => {
                    setUserDropdownOpen(false);
                    onOpenAuth();
                  }}
                  className="w-full text-left px-3.5 py-2 text-[#011405] hover:bg-[#f7fef8] flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <User className="w-3.5 h-3.5 text-[#55785d]" />
                  <span>Account Session</span>
                </button>

                <button
                  onClick={() => {
                    setUserDropdownOpen(false);
                    onOpenActivityLog();
                  }}
                  className="w-full text-left px-3.5 py-2 text-[#011405] hover:bg-[#f7fef8] flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-[#16d639]" />
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