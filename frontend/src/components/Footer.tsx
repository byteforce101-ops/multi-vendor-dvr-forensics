import React from 'react';

interface FooterProps {
  onOpenCompliance: (tab: 'security' | 'compliance' | 'api') => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenCompliance }) => {
  return (
    <footer className="w-full mt-20 border-t border-[#ded4c5] bg-transparent py-8">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left Copyright */}
        <div className="text-[11px] font-medium text-[#7d7367] uppercase tracking-widest font-['DM_Sans',sans-serif]">
          © 2024 TRACEX AI FORENSICS • NIST SP 800-86 AUDITED
        </div>

        {/* Right Navigation Links */}
        <div className="flex items-center space-x-6 text-[12.5px] font-medium text-[#5c544c]">
          <button
            id="footer-link-security"
            onClick={() => onOpenCompliance('security')}
            className="hover:text-[#0f2338] transition-colors cursor-pointer"
          >
            Security & Encryption
          </button>
          <button
            id="footer-link-compliance"
            onClick={() => onOpenCompliance('compliance')}
            className="hover:text-[#0f2338] transition-colors cursor-pointer"
          >
            CJIS Compliance
          </button>
          <button
            id="footer-link-apidocs"
            onClick={() => onOpenCompliance('api')}
            className="hover:text-[#0f2338] transition-colors cursor-pointer"
          >
            API Docs
          </button>
        </div>
      </div>
    </footer>
  );
};
