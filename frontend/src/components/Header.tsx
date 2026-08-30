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
    <header
      className="w-full sticky top-0 z-30 backdrop-blur-md transition-colors"
      style={{ background: 'color-mix(in srgb, var(--color-panel) 95%, transparent)', borderBottom: '1px solid var(--color-brd)' }}
    >
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 h-12 flex items-center justify-between">
        {/* Left: Sidebar Toggle & Brand */}
        <div className="flex items-center gap-3">
          <button
            id="nav-hamburger-btn"
            onClick={onToggleSidebar}
            className="w-8 h-8 flex items-center justify-center rounded transition-colors hover:bg-[var(--color-teal-light)] cursor-pointer focus:outline-none"
            style={{ color: 'var(--color-txt2)' }}
            aria-label="Toggle sidebar menu"
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <Menu className="w-4 h-4" strokeWidth={1.9} />
          </button>

          <div
            onClick={() => {
              if (onNavigateToArchitecture) onNavigateToArchitecture();
              else onNavChange('Pipelines');
            }}
            className="flex items-center gap-2 cursor-pointer group"
            title="TraceX - Click to view Architecture & Platform Capabilities"
          >
            <TraceXLogo size={28} variant="gold" bgColor="#0f1715" />
            <span
              className="text-[16px] font-semibold tracking-tight transition-colors"
              style={{ color: 'var(--color-txt)' }}
            >
              TraceX
            </span>
          </div>
        </div>

        {/* Right: User Profile */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <button
              id="user-profile-btn"
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2.5 text-right group py-1 px-2 rounded transition-colors hover:bg-[var(--color-teal-light)] border border-transparent cursor-pointer"
            >
              <div className="hidden sm:block leading-tight text-right">
                <div className="text-[13px] font-medium tracking-tight" style={{ color: 'var(--color-txt)' }}>
                  {user.name}
                </div>
                <div className="mono text-[11px]" style={{ color: 'var(--color-txt2)' }}>
                  {user.enterpriseId}
                </div>
              </div>

              <div
                className="w-7 h-7 rounded flex items-center justify-center text-xs font-semibold text-white relative"
                style={{ background: 'var(--color-teal)' }}
              >
                <User className="w-3.5 h-3.5" />
                <span
                  className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border-2"
                  style={{ background: 'var(--color-mgreen)', borderColor: 'var(--color-panel)' }}
                />
              </div>
            </button>

            {userDropdownOpen && (
              <div
                className="absolute right-0 mt-2 w-64 rounded py-1.5 z-50"
                style={{ background: 'var(--color-panel)', border: '1px solid var(--color-brd)', boxShadow: '0 8px 24px rgba(23,38,48,0.12)' }}
                onClick={() => setUserDropdownOpen(false)}
              >
                <div className="px-4 py-2.5" style={{ borderBottom: '1px solid var(--color-brd)' }}>
                  <p className="text-xs font-semibold" style={{ color: 'var(--color-txt)' }}>{user.name}</p>
                  <p className="text-xs truncate" style={{ color: 'var(--color-txt2)' }}>{user.email}</p>
                </div>

                <button
                  onClick={onOpenAuth}
                  className="w-full text-left px-4 py-2 text-xs flex items-center gap-2 cursor-pointer transition-colors hover:bg-[var(--color-teal-light)]"
                  style={{ color: 'var(--color-txt)' }}
                >
                  <Key className="w-3.5 h-3.5" style={{ color: 'var(--color-teal)' }} />
                  <span>Profile & Session</span>
                </button>

                <button
                  onClick={onOpenActivityLog}
                  className="w-full text-left px-4 py-2 text-xs flex items-center gap-2 cursor-pointer transition-colors hover:bg-[var(--color-teal-light)]"
                  style={{ color: 'var(--color-txt)' }}
                >
                  <ShieldCheck className="w-3.5 h-3.5" style={{ color: 'var(--color-mgreen)' }} />
                  <span>Activity Log</span>
                </button>

                <div className="my-1" style={{ borderTop: '1px solid var(--color-brd)' }} />

                <button
                  onClick={onOpenAuth}
                  className="w-full text-left px-4 py-2 text-xs flex items-center gap-2 cursor-pointer transition-colors hover:bg-[var(--color-crit-light)]"
                  style={{ color: 'var(--color-crit)' }}
                >
                  <LogOut className="w-3.5 h-3.5" />
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