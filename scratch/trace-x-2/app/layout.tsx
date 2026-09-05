import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Trace-X | Forensic Investigation Workstation',
  description: 'Professional video forensics for evidence, entities, events and integrity analysis.',
  generator: 'Trace-X',
}

export const viewport: Viewport = {
  colorScheme: 'light',
  themeColor: '#172554',
  userScalable: true,
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="bg-[#f5f6f7]"><body className="antialiased">{children}{process.env.NODE_ENV === 'production' && <Analytics />}</body></html>
}
