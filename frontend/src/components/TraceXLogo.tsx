import React from 'react';
import logo from '../assets/tracex-logo.png.png';

interface TraceXLogoProps {
  className?: string;
}

const TraceXLogo: React.FC<TraceXLogoProps> = ({
  className = '',
}) => {
  return (
    <img
      src={logo}
      alt="TraceX Forensics Studio"
      className={`h-9 w-auto object-contain ${className}`}
    />
  );
};

export default TraceXLogo;