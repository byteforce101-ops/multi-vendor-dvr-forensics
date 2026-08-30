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
        transition={{ type: 'spring', damping: 28, stiffness: 320 }}
        className="fixed top-0 left-0 h-screen w-[280px] z-50 flex flex-col justify-between overflow-hidden bg-white/95 backdrop-blur-xl border-r border-slate-200/90 shadow-2xl"
      >
        <div className="w-full h-full flex flex-col justify-between p-5 overflow-y-auto">
          {/* Top Brand Header */}
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div
                onClick={() => {
                  onNavChange('Pipelines');
                  onToggle();
                }}
                className="flex items-center space-x-2.5 cursor-pointer group"
              >
                <div className="w-8 h-8 rounded-md bg-blue-800 flex items-center justify-center text-white font-bold text-xs shadow-xs group-hover:bg-blue-900 transition-colors">
                  <span>TX</span>
                </div>
                <div>
                  <span className="text-[16px] font-bold tracking-tight text-slate-900 block leading-none">
                    TraceX
                  </span>
                  <span className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase mt-1 block">
                    Forensics Studio
                  </span>
                </div>
              </div>

              <button
                onClick={onToggle}
                className="w-7 h-7 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors flex items-center justify-center cursor-pointer"
                title="Close sidebar"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Navigation Buttons Group */}
            <div className="mt-5 space-y-1">
              <div className="px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase text-slate-400">
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
                    className={`w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                      isActive
                        ? 'bg-blue-50 text-blue-900 font-semibold border-l-4 border-blue-800 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <Icon size={16} className={isActive ? 'text-blue-800' : 'text-slate-400'} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate">{item.label}</div>
                      <div className="text-[10px] text-slate-400 font-normal truncate">{item.description}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Compliance & Audit */}
            <div className="mt-6 pt-4 border-t border-slate-100 space-y-1">
              <div className="px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase text-slate-400">
                Audit & Compliance
              </div>

              <button
                onClick={() => {
                  onOpenActivityLog();
                  onToggle();
                }}
                className="w-full text-left flex items-center justify-between px-3 py-2 rounded-lg text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Chain of Custody</span>
                </div>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              </button>

              <button
                onClick={() => {
                  onOpenCompliance('security');
                  onToggle();
                }}
                className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors cursor-pointer"
              >
                <FileCheck className="w-4 h-4 text-blue-700" />
                <span>Forensic Standards</span>
              </button>
            </div>
          </div>

          {/* Bottom Profile & Session Section */}
          <div className="pt-4 border-t border-slate-100 space-y-2">
            <button
              id="sidebar-btn-profile"
              onClick={() => {
                onOpenProfile();
                onToggle();
              }}
              className="w-full text-left p-2.5 rounded-lg border border-slate-200 hover:border-slate-300 bg-slate-50 hover:bg-white transition-all flex items-center gap-2.5 cursor-pointer shadow-xs"
            >
              <div className="w-7 h-7 rounded-md bg-blue-50 text-blue-800 border border-blue-200 flex items-center justify-center font-bold text-xs shrink-0">
                {user.name.charAt(0).toUpperCase()}
              </div>

              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-slate-900 truncate">{user.name}</div>
                <div className="text-[10px] text-slate-400 truncate">{user.email || 'Investigator'}</div>
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
