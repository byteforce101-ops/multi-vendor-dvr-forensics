import React from 'react';
import logoOriginal from '../assets/tracex-logo.png';
import logoWhite from '../assets/tracex-logo-white.png';
import logoDark from '../assets/tracex-logo-dark.png';

interface TraceXLogoProps {
  className?: string;
  variant?: 'white' | 'dark' | 'original';
  alt?: string;
}

const TraceXLogo: React.FC<TraceXLogoProps> = ({
  className = '',
  variant = 'original',
  alt = 'TRACEX Forensics Platform',
}) => {
  const src = variant === 'white' ? logoWhite : variant === 'dark' ? logoDark : logoOriginal;
  const hasHeight = /\bh-/.test(className);

  return (
    <img
      src={src}
      alt={alt}
      className={`${hasHeight ? '' : 'h-10'} w-auto object-contain ${className}`.trim()}
    />
  );
};

export default TraceXLogo;