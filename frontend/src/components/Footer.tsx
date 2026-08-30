import React from 'react';

interface FooterProps {
  onOpenCompliance: (tab: 'security' | 'compliance' | 'api') => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenCompliance }) => {
  return (
    <footer className="w-full mt-16 border-t border-[#d2ecd6] bg-white py-6">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#2d4a34]">
        <div>
          © 2024 TraceX Forensic Intelligence • NIST SP 800-86 & ISO/IEC 27037 Compliant
        </div>

        <div className="flex items-center space-x-4">
          <button
            id="footer-link-security"
            onClick={() => onOpenCompliance('security')}
            className="hover:text-[#011405] transition-colors cursor-pointer"
          >
            Security & Cryptography
          </button>
          <span className="text-[#bde3c3]">•</span>
          <button
            id="footer-link-compliance"
            onClick={() => onOpenCompliance('compliance')}
            className="hover:text-[#011405] transition-colors cursor-pointer"
          >
            CJIS / ISO Compliance
          </button>
          <span className="text-[#bde3c3]">•</span>
          <button
            id="footer-link-apidocs"
            onClick={() => onOpenCompliance('api')}
            className="hover:text-[#011405] transition-colors cursor-pointer"
          >
            API Specifications
          </button>
        </div>
      </div>
    </footer>
  );
};

