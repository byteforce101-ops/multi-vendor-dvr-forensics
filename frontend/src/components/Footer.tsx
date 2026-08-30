import React from 'react';

interface FooterProps {
  onOpenCompliance: (tab: 'security' | 'compliance' | 'api') => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenCompliance }) => {
  return (
    <footer className="w-full mt-16 border-t border-slate-200 bg-white/60 py-6">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
        <div>
          TraceX 
        </div>

        <div className="flex items-center space-x-4">
          <button
            id="footer-link-security"
            onClick={() => onOpenCompliance('security')}
            className="hover:text-slate-900 transition-colors cursor-pointer"
          >
            Security & Cryptography
          </button>
          <span className="text-slate-300">•</span>
          <button
            id="footer-link-compliance"
            onClick={() => onOpenCompliance('compliance')}
            className="hover:text-slate-900 transition-colors cursor-pointer"
          >
            CJIS / ISO Compliance
          </button>
          <span className="text-slate-300">•</span>
          <button
            id="footer-link-apidocs"
            onClick={() => onOpenCompliance('api')}
            className="hover:text-slate-900 transition-colors cursor-pointer"
          >
            API Specifications
          </button>
        </div>
      </div>
    </footer>
  );
};

