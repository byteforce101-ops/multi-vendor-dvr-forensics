import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

export const isSupabaseConfigured = Boolean(url && key && !url.includes('YOUR_') && !key.includes('YOUR_'))
export const supabase = isSupabaseConfigured ? createClient(url, key) : null
