import React from 'react';

interface TraceXLogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
  textColor?: string;
  variant?: 'cyan' | 'orange' | 'gold' | 'dark' | 'light';
  bgColor?: string;
}

export const TraceXLogo: React.FC<TraceXLogoProps> = ({
  size = 32,
  className = '',
  showText = false,
  textColor = '#F1F5F9',
  variant = 'cyan',
  bgColor,
}) => {
  const gradientId = `tracex-cyber-grad-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div className={`inline-flex items-center gap-2.5 select-none ${className}`}>
      <div 
        className="relative flex items-center justify-center rounded-lg overflow-hidden transition-all"
        style={{
          width: size,
          height: size,
          backgroundColor: bgColor || '#0D192E',
          border: '1px solid #1E3A5F',
          boxShadow: '0 0 14px rgba(0, 210, 255, 0.15)',
        }}
      >
        <svg
          width={size * 0.75}
          height={size * 0.75}
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              {variant === 'orange' ? (
                <>
                  <stop offset="0%" stopColor="#FFAE42" />
                  <stop offset="100%" stopColor="#FF6B00" />
                </>
              ) : (
                <>
                  <stop offset="0%" stopColor="#00D2FF" />
                  <stop offset="50%" stopColor="#0284C7" />
                  <stop offset="100%" stopColor="#0369A1" />
                </>
              )}
            </linearGradient>
          </defs>

          {/* TraceX Stylized Cyber Concentric Fingerprint & Shield Ridges */}
          <path
            d="M 50 12 C 72 12 88 28 88 50 C 88 62 82 72 74 79"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M 40 13 C 24 18 12 33 12 50 C 12 58 15 65 20 71"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M 50 24 C 65 24 76 36 76 51 C 76 65 71 74 65 82"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M 33 26 C 24 33 22 42 22 51 C 22 62 26 71 34 78"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M 50 36 C 58 36 64 43 64 52 C 64 68 59 78 54 85"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M 36 43 C 33 46 32 50 32 55 C 32 67 38 78 44 85"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M 50 48 C 52 48 53 50 53 53 C 53 65 50 73 47 79"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {showText && (
        <div className="flex flex-col">
          <span 
            className="text-[16px] font-bold tracking-wider font-['Inter',sans-serif] uppercase"
            style={{ color: textColor }}
          >
            TraceX
          </span>
          <span className="text-[9px] font-mono tracking-widest uppercase text-[#00D2FF] font-semibold -mt-0.5">
            Cyber Forensics
          </span>
        </div>
      )}
    </div>
  );
};

