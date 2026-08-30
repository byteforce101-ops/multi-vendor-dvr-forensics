/// <reference types="vite/client" />
import { createClient } from '@supabase/supabase-js';
import { SupabaseUser } from '../types';

const metaEnv = (import.meta as unknown as { env?: Record<string, string> }).env || {};
const supabaseUrl = metaEnv.VITE_SUPABASE_URL || '';
const supabaseAnonKey = metaEnv.VITE_SUPABASE_PUBLISHABLE_KEY || metaEnv.VITE_SUPABASE_ANON_KEY || '';

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

export const DEFAULT_USER: SupabaseUser = {
  id: 'usr_ent_9924820',
  email: 'enterprise-ops@visionstream.ai',
  role: 'Senior Forensic Analyst',
  enterpriseId: '10D11A8',
  name: 'Enterprise User',
  isLoggedIn: true,
};