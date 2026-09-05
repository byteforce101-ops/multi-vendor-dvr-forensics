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

  return (
    <img
      src={src}
      alt={alt}
      className={`h-8 w-auto object-contain ${className}`}
    />
  );
};

export default TraceXLogo;