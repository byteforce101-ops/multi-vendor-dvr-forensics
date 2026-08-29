import React from 'react';

interface TraceXLogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
  textColor?: string;
  variant?: 'gold' | 'emerald' | 'dark' | 'light';
  bgColor?: string;
}

export const TraceXLogo: React.FC<TraceXLogoProps> = ({
  size = 32,
  className = '',
  showText = false,
  textColor = '#221e1b',
  variant = 'gold',
  bgColor,
}) => {
  // Color palette for the stylized biometric fingerprint ridges
  const strokeColor = 
    variant === 'gold' ? '#d4af37' :
    variant === 'emerald' ? '#2d6a4f' :
    variant === 'light' ? '#fcfbf8' : '#1e1b18';

  const gradientId = `tracex-gold-grad-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div className={`inline-flex items-center gap-2.5 select-none ${className}`}>
      <div 
        className="relative flex items-center justify-center rounded-xl overflow-hidden transition-transform group-hover:scale-105"
        style={{
          width: size,
          height: size,
          backgroundColor: bgColor || (variant === 'gold' ? '#0f1715' : 'transparent'),
          boxShadow: bgColor ? '0 2px 8px -1px rgba(0,0,0,0.15)' : 'none',
        }}
      >
        <svg
          width={size * 0.85}
          height={size * 0.85}
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              {variant === 'gold' ? (
                <>
                  <stop offset="0%" stopColor="#f5df88" />
                  <stop offset="45%" stopColor="#d4af37" />
                  <stop offset="75%" stopColor="#aa8222" />
                  <stop offset="100%" stopColor="#eed77e" />
                </>
              ) : (
                <>
                  <stop offset="0%" stopColor="#52b788" />
                  <stop offset="100%" stopColor="#1b4332" />
                </>
              )}
            </linearGradient>
          </defs>

          {/* TraceX Stylized Concentric Fingerprint Ridges */}
          {/* Ridge 1 - Outer ring segments */}
          <path
            d="M 50 12 C 72 12 88 28 88 50 C 88 62 82 72 74 79"
            stroke={`url(#${gradientId})`}
            strokeWidth="5.5"
            strokeLinecap="round"
          />
          <path
            d="M 40 13 C 24 18 12 33 12 50 C 12 58 15 65 20 71"
            stroke={`url(#${gradientId})`}
            strokeWidth="5.5"
            strokeLinecap="round"
          />

          {/* Ridge 2 - Second tier arches */}
          <path
            d="M 50 24 C 65 24 76 36 76 51 C 76 65 71 74 65 82"
            stroke={`url(#${gradientId})`}
            strokeWidth="5.5"
            strokeLinecap="round"
          />
          <path
            d="M 33 26 C 24 33 22 42 22 51 C 22 62 26 71 34 78"
            stroke={`url(#${gradientId})`}
            strokeWidth="5.5"
            strokeLinecap="round"
          />

          {/* Ridge 3 - Core biometric loop */}
          <path
            d="M 50 36 C 58 36 64 43 64 52 C 64 68 59 78 54 85"
            stroke={`url(#${gradientId})`}
            strokeWidth="5.5"
            strokeLinecap="round"
          />
          <path
            d="M 36 43 C 33 46 32 50 32 55 C 32 67 38 78 44 85"
            stroke={`url(#${gradientId})`}
            strokeWidth="5.5"
            strokeLinecap="round"
          />

          {/* Ridge 4 - Innermost whorl & apex */}
          <path
            d="M 50 48 C 52 48 53 50 53 53 C 53 65 50 73 47 79"
            stroke={`url(#${gradientId})`}
            strokeWidth="5.5"
            strokeLinecap="round"
          />
          <path
            d="M 43 56 C 43 63 45 70 47 76"
            stroke={`url(#${gradientId})`}
            strokeWidth="5"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {showText && (
        <div className="flex flex-col">
          <span 
            className="text-[18px] font-extrabold tracking-wider font-['Manrope'] uppercase"
            style={{ color: textColor }}
          >
            TraceX
          </span>
          <span className="text-[9.5px] font-mono tracking-widest uppercase text-[#236446] font-bold -mt-0.5">
            Forensic Intelligence
          </span>
        </div>
      )}
    </div>
  );
};
