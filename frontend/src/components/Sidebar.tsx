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
  ChevronRight,
  Sparkles,
  Database,
  Key,
  X,
  FileCheck
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
    {
      id: 'Pipelines',
      label: 'Pipelines',
      icon: Layers,
      tag: 'Workflow',
      description: 'Ingest & processing pipeline',
    },
    {
      id: 'Analyses',
      label: 'Analyses',
      icon: Activity,
      tag: 'Forensics',
      description: 'AI object & event chronology',
    },
    {
      id: 'Library',
      label: 'Library',
      icon: FolderArchive,
      tag: 'Vault',
      description: 'Hashed evidence repository',
    },
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
            className="fixed inset-0 bg-[#1e1b18]/40 backdrop-blur-xs z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* Sidebar Container */}
      <motion.aside
        initial={false}
        animate={{
          width: isOpen ? 280 : 0,
          opacity: isOpen ? 1 : 0,
        }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        className={`fixed lg:sticky top-0 left-0 h-screen z-50 lg:z-30 bg-[#fcfbf8] border-r border-[#ded5c7] flex flex-col justify-between overflow-hidden shadow-sm ${
          isOpen ? 'pointer-events-auto' : 'pointer-events-none lg:pointer-events-none'
        }`}
      >
        <div className="w-[280px] h-full flex flex-col justify-between p-5 overflow-y-auto scrollbar-none">
          {/* Top Brand Header */}
          <div>
            <div className="flex items-center justify-between pb-5 border-b border-[#eee6da]">
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
                {/* TraceX Golden Fingerprint Logo */}
                <TraceXLogo size={36} variant="gold" bgColor="#0f1715" />
                <div>
                  <span className="text-[20px] font-extrabold tracking-tight text-[#221e1b] font-['Manrope'] block leading-none group-hover:text-[#1b4e39] transition-colors">
                    TraceX
                  </span>
                  <span className="text-[10.5px] font-mono text-[#1b4e39] font-bold tracking-wider uppercase mt-1 block">
                    Forensic AI
                  </span>
                </div>
              </div>

              {/* Close / Collapse Toggle button */}
              <button
                onClick={onToggle}
                className="p-1.5 rounded-lg text-[#635b52] hover:text-[#221e1b] hover:bg-[#f3ede2] transition-colors cursor-pointer"
                title="Collapse sidebar"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            </div>

            {/* Navigation Buttons Group */}
            <div className="mt-6 space-y-1.5">
              <div className="text-[10.5px] font-bold uppercase tracking-[0.18em] text-[#7d7367] px-3 mb-2 font-['Manrope']">
                Workspace
              </div>

              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeNav === item.id;

                return (
                  <button
                    key={item.id}
                    id={`sidebar-btn-${item.id.toLowerCase()}`}
                    onClick={() => {
                      onNavChange(item.id);
                      if (window.innerWidth < 1024) {
                        onToggle();
                      }
                    }}
                    className={`w-full text-left px-3.5 py-3 rounded-xl text-[13.5px] font-medium transition-all flex items-center justify-between group relative cursor-pointer ${
                      isActive
                        ? 'bg-[#0f2338] text-white shadow-md shadow-[#0f2338]/20 font-semibold'
                        : 'text-[#3d3630] hover:bg-[#f4ede2] hover:text-[#0f2338]'
                    }`}
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <Icon
                        className={`w-4 h-4 transition-transform group-hover:scale-110 ${
                          isActive ? 'text-white stroke-[2.4]' : 'text-[#3b5749] stroke-[2]'
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>

                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-md uppercase font-semibold ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : 'bg-[#ede5d8] text-[#5c544c] group-hover:bg-[#e4dbcd]'
                      }`}
                    >
                      {item.tag}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Secondary Audit & Security Links */}
            <div className="mt-7 pt-5 border-t border-[#eee6da] space-y-1.5">
              <div className="text-[10.5px] font-bold uppercase tracking-[0.18em] text-[#7d7367] px-3 mb-2 font-['Manrope']">
                Forensic Ledger
              </div>

              <button
                onClick={onOpenActivityLog}
                className="w-full text-left px-3.5 py-2.5 rounded-xl text-[12.5px] text-[#3d3630] hover:bg-[#f4ede2] hover:text-[#0f2338] flex items-center justify-between transition-colors group cursor-pointer"
              >
                <div className="flex items-center space-x-2.5">
                  <ShieldCheck className="w-4 h-4 text-[#3b5749]" />
                  <span>Chain of Custody</span>
                </div>
                <span className="w-2 h-2 rounded-full bg-[#3b5749]"></span>
              </button>

              <button
                onClick={() => onOpenCompliance('security')}
                className="w-full text-left px-3.5 py-2.5 rounded-xl text-[12.5px] text-[#3d3630] hover:bg-[#f4ede2] hover:text-[#0f2338] flex items-center space-x-2.5 transition-colors cursor-pointer"
              >
                <FileCheck className="w-4 h-4 text-[#3b5749]" />
                <span>Forensic Standards</span>
              </button>
            </div>
          </div>

          {/* Bottom Profile & Logout Section */}
          <div className="pt-5 border-t border-[#eee6da] space-y-3">
            {/* User Profile Card / Button */}
            <button
              id="sidebar-btn-profile"
              onClick={onOpenProfile}
              className="w-full text-left p-3 rounded-2xl bg-[#f5efe4] hover:bg-[#ebe3d5] border border-[#ded5c7] transition-all group flex items-center space-x-3 cursor-pointer shadow-2xs"
            >
              {/* Navy Avatar */}
              <div className="w-9 h-9 rounded-xl bg-[#0f2338] text-white flex items-center justify-center text-xs font-bold shadow-xs relative flex-shrink-0 group-hover:scale-105 transition-transform">
                <User className="w-4 h-4" />
                <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-[#3b5749] border-2 border-[#f5efe4] rounded-full"></span>
              </div>

              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-bold text-[#221e1b] truncate group-hover:text-[#0f2338]">
                  {user.name}
                </div>
                <div className="text-[11px] font-mono text-[#6e6459] truncate">
                  ID: {user.enterpriseId}
                </div>
              </div>

              <span className="text-[10px] font-mono text-[#3b5749] bg-[#eaf1ed] border border-[#c9dcd0] px-1.5 py-0.5 rounded font-semibold uppercase">
                RBAC
              </span>
            </button>

            {/* Logout / Switch Session Button */}
            <button
              id="sidebar-btn-logout"
              onClick={onLogout}
              className="w-full text-left px-3.5 py-2.5 rounded-xl text-[12.5px] font-semibold text-[#c2593f] hover:bg-rose-50 hover:text-[#a8442c] flex items-center justify-between transition-colors cursor-pointer group"
            >
              <div className="flex items-center space-x-2.5">
                <LogOut className="w-4 h-4 text-[#c2593f] group-hover:-translate-x-0.5 transition-transform" />
                <span>Log Out / Switch Session</span>
              </div>
              <span className="text-[10px] font-mono text-[#8c8275]">Exit</span>
            </button>
          </div>
        </div>
      </motion.aside>
    </>
  );
};
