import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Layers,
  Activity,
  FolderArchive,
  User,
  LogOut,
  ShieldCheck,
  X,
  FileCheck,
} from 'lucide-react';
import { SupabaseUser } from '../types';

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
}) => {
  const navItems = [
    { id: 'Pipelines', label: 'Evidence Ingest', icon: Layers, description: 'File upload & SHA-256 seal' },
    { id: 'Analyses', label: 'Forensic Analytics', icon: Activity, description: 'Stream integrity & AI query' },
    { id: 'Library', label: 'Evidence Vault', icon: FolderArchive, description: 'Verified repository' },
  ] as const;

  return (
    <>
      {/* Backdrop (closes sidebar on click) */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
            className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs z-40 transition-opacity"
          />
        )}
      </AnimatePresence>

      {/* Slide-out Sidebar Drawer */}
      <motion.aside
        initial={false}
        animate={{
          x: isOpen ? 0 : -280,
          opacity: isOpen ? 1 : 0,
        }}
        transition={{ type: 'spring', damping: 25, stiffness: 280 }}
        className="fixed top-0 left-0 h-screen w-[280px] z-50 flex flex-col justify-between overflow-hidden bg-white border-r border-[#d2ecd6] shadow-xl"
      >
        <div className="w-full h-full flex flex-col justify-between p-5 overflow-y-auto">
          {/* Top Brand Header */}
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-[#e3f6e6]">
              <div
                onClick={() => {
                  onNavChange('Pipelines');
                  onToggle();
                }}
                className="flex items-center space-x-2.5 cursor-pointer"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#415ef4] to-[#1cf243] flex items-center justify-center text-white font-black text-xs shadow-xs">
                  <span>TX</span>
                </div>
                <div>
                  <span className="text-[16px] font-bold tracking-tight text-[#011405] block leading-none">
                    TraceX
                  </span>
                  <span className="text-[10px] text-[#2d4a34] font-medium tracking-wide uppercase mt-0.5 block">
                    Forensics OS
                  </span>
                </div>
              </div>

              <button
                onClick={onToggle}
                className="w-7 h-7 rounded-lg text-[#55785d] hover:text-[#011405] hover:bg-[#e8f9ec] transition-colors flex items-center justify-center cursor-pointer"
                title="Close sidebar"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Navigation Buttons Group */}
            <div className="mt-5 space-y-1">
              <div className="px-3 py-1.5 text-[11px] font-semibold tracking-wider uppercase text-[#55785d]">
                Navigation
              </div>

              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeNav === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavChange(item.id);
                      onToggle();
                    }}
                    className={`w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                      isActive
                        ? 'bg-[#e6faea] text-[#011405] font-bold border-l-4 border-[#1cf243] shadow-xs'
                        : 'text-[#2d4a34] hover:text-[#011405] hover:bg-[#f7fef8]'
                    }`}
                  >
                    <Icon size={16} className={isActive ? 'text-[#16d639]' : 'text-[#74b8f7]'} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate">{item.label}</div>
                      <div className="text-[10px] text-[#55785d] font-normal truncate">{item.description}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Compliance & Audit */}
            <div className="mt-6 pt-4 border-t border-[#e3f6e6] space-y-1">
              <div className="px-3 py-1.5 text-[11px] font-semibold tracking-wider uppercase text-[#55785d]">
                Audit & Compliance
              </div>

              <button
                onClick={() => {
                  onOpenActivityLog();
                  onToggle();
                }}
                className="w-full text-left flex items-center justify-between px-3 py-2 rounded-lg text-xs text-[#2d4a34] hover:text-[#011405] hover:bg-[#f7fef8] transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-[#16d639]" />
                  <span>Chain of Custody</span>
                </div>
                <span className="w-1.5 h-1.5 rounded-full bg-[#1cf243]" />
              </button>

              <button
                onClick={() => {
                  onOpenCompliance('security');
                  onToggle();
                }}
                className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-[#2d4a34] hover:text-[#011405] hover:bg-[#f7fef8] transition-colors cursor-pointer"
              >
                <FileCheck className="w-4 h-4 text-[#415ef4]" />
                <span>Forensic Standards</span>
              </button>
            </div>
          </div>

          {/* Bottom Profile & Session Section */}
          <div className="pt-4 border-t border-[#e3f6e6] space-y-2">
            <button
              id="sidebar-btn-profile"
              onClick={() => {
                onOpenProfile();
                onToggle();
              }}
              className="w-full text-left p-2.5 rounded-xl border border-[#d2ecd6] hover:border-[#bde3c3] bg-[#f7fef8] hover:bg-white transition-all flex items-center gap-2.5 cursor-pointer shadow-xs"
            >
              <div className="w-7 h-7 rounded-full bg-[#e8f9ec] text-[#011405] border border-[#d2ecd6] flex items-center justify-center font-bold text-xs shrink-0">
                {user.name.charAt(0).toUpperCase()}
              </div>

              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-[#011405] truncate">{user.name}</div>
                <div className="text-[10px] text-[#55785d] truncate">{user.email || 'Investigator'}</div>
              </div>
            </button>

            <button
              id="sidebar-btn-logout"
              onClick={() => {
                onLogout();
                onToggle();
              }}
              className="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer flex items-center gap-2"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </motion.aside>
    </>
  );
};
