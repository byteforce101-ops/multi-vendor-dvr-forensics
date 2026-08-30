import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Layers,
  Activity,
  FolderArchive,
  User,
  LogOut,
  ShieldCheck,
  ChevronLeft,
  FileCheck,
} from 'lucide-react';
import { SupabaseUser } from '../types';
import { TraceXLogo } from './TraceXLogo';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  activeNav: string;
  onNavChange: (nav: 'Pipelines' | 'Analyses' | 'Library') => void;
  user: SupabaseUser;
  onOpenProfile: () => void;
  onLogout: () => void;
  onOpenActivityLog: () => void;
  onOpenCompliance: (tab: 'security' | 'compliance' | 'api') => void;
  onNavigateToArchitecture?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onToggle,
  activeNav,
  onNavChange,
  user,
  onOpenProfile,
  onLogout,
  onOpenActivityLog,
  onOpenCompliance,
  onNavigateToArchitecture,
}) => {
  const navItems = [
    { id: 'Pipelines', label: 'Pipelines', icon: Layers, description: 'Ingest & processing pipeline' },
    { id: 'Analyses', label: 'Analyses', icon: Activity, description: 'AI object & event chronology' },
    { id: 'Library', label: 'Library', icon: FolderArchive, description: 'Hashed evidence repository' },
  ] as const;

  return (
    <>
      {/* Mobile Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* Sidebar Container */}
      <motion.aside
        initial={false}
        animate={{ width: isOpen ? 280 : 0, opacity: isOpen ? 1 : 0 }}
        transition={{ duration: 0.2 }}
        style={{ background: 'var(--color-sidebar)', borderRight: '1px solid rgba(255,255,255,0.06)' }}
        className="fixed lg:sticky top-0 left-0 h-screen z-50 lg:z-30 flex flex-col justify-between overflow-hidden"
      >
        <div className="w-[280px] h-full flex flex-col justify-between p-5 overflow-y-auto scrollbar-none">
          {/* Top Brand Header */}
          <div>
            <div className="flex items-center justify-between pb-5 border-b border-white/5">
              <div
                onClick={() => {
                  if (onNavigateToArchitecture) {
                    onNavigateToArchitecture();
                  } else {
                    onNavChange('Pipelines');
                  }
                }}
                className="flex items-center space-x-3 cursor-pointer group"
                title="TraceX - Click to view Architecture & Platform Capabilities"
              >
                <TraceXLogo size={36} variant="gold" bgColor="#0f1715" />
                <div>
                  <span className="text-[18px] font-semibold tracking-tight text-white block leading-none group-hover:text-[#7ec8d8] transition-colors">
                    TraceX
                  </span>
                  <span className="text-[10px] mono text-white/35 font-medium tracking-widest uppercase mt-1 block">
                    Forensic AI
                  </span>
                </div>
              </div>

              <button
                onClick={onToggle}
                className="p-1.5 rounded text-white/40 hover:text-white/70 hover:bg-white/5 transition-colors cursor-pointer shrink-0"
                title="Collapse sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>

            {/* Navigation Buttons Group */}
            <div className="mt-6 space-y-1">
              <div
                className="px-2 py-2 text-[10px] font-semibold tracking-widest uppercase"
                style={{ color: 'rgba(255,255,255,0.22)' }}
              >
                Workspace
              </div>

              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeNav === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavChange(item.id);
                      if (window.innerWidth < 1024) onToggle();
                    }}
                    className={`sidebar-item w-full text-left ${isActive ? 'active' : ''}`}
                  >
                    <Icon size={14} strokeWidth={1.75} className="shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Secondary Audit & Security Links */}
            <div className="mt-7 pt-5 border-t border-white/5 space-y-1">
              <div
                className="px-2 py-2 text-[10px] font-semibold tracking-widest uppercase"
                style={{ color: 'rgba(255,255,255,0.22)' }}
              >
                Forensic Ledger
              </div>

              <button
                onClick={onOpenActivityLog}
                className="sidebar-item w-full text-left justify-between"
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-3.5 h-3.5" style={{ color: 'var(--color-mgreen)' }} />
                  <span>Chain of Custody</span>
                </div>
                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: 'var(--color-mgreen)' }} />
              </button>

              <button
                onClick={() => onOpenCompliance('security')}
                className="sidebar-item w-full text-left"
              >
                <FileCheck className="w-3.5 h-3.5" style={{ color: 'var(--color-mgreen)' }} />
                <span>Forensic Standards</span>
              </button>
            </div>
          </div>

          {/* Bottom Profile & Logout Section */}
          <div className="pt-5 border-t border-white/5 space-y-2">
            <button
              id="sidebar-btn-profile"
              onClick={onOpenProfile}
              className="w-full text-left p-3 rounded transition-all group flex items-center gap-3 cursor-pointer"
              style={{ background: 'rgba(65,99,110,0.18)', border: '1px solid rgba(65,99,110,0.3)' }}
            >
              <div
                className="w-8 h-8 rounded flex items-center justify-center text-xs font-semibold text-white relative flex-shrink-0"
                style={{ background: 'var(--color-teal)' }}
              >
                <User className="w-4 h-4" />
                <span
                  className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border-2"
                  style={{ background: 'var(--color-mgreen)', borderColor: 'var(--color-sidebar)' }}
                />
              </div>

              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium text-white truncate">{user.name}</div>
                <div className="mono text-[11px] text-white/40 truncate">ID: {user.enterpriseId}</div>
              </div>

              <span
                className="text-[10px] mono px-1.5 py-0.5 rounded font-semibold uppercase shrink-0"
                style={{ background: 'rgba(65,99,110,0.3)', color: '#7ec8d8' }}
              >
                RBAC
              </span>
            </button>

            <button
              id="sidebar-btn-logout"
              onClick={onLogout}
              className="w-full text-left px-3 py-2.5 rounded text-[12.5px] font-medium flex items-center justify-between transition-colors cursor-pointer group"
              style={{ color: 'var(--color-crit)' }}
            >
              <div className="flex items-center gap-2.5">
                <LogOut className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
                <span>Log Out / Switch Session</span>
              </div>
              <span className="text-[10px] mono text-white/25">Exit</span>
            </button>
          </div>
        </div>
      </motion.aside>
    </>
  );
};