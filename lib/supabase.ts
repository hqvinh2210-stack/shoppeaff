import { createClient } from "@supabase/supabase-js";

// Chỉ dùng ở server (Route Handlers) - KHÔNG import file này trong client component.
// Ưu tiên SUPABASE_SERVICE_ROLE_KEY nếu có. Nếu chưa có service role thì tạm dùng
// SUPABASE_PUBLISHABLE_KEY để test các endpoint có policy RLS phù hợp.
const supabaseUrl = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey =
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_PUBLISHABLE_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export function getSupabaseAdmin() {
  if (!supabaseUrl || !supabaseKey) {
    throw new Error(
      "Thiếu SUPABASE_URL/NEXT_PUBLIC_SUPABASE_URL hoặc SUPABASE_SERVICE_ROLE_KEY/SUPABASE_PUBLISHABLE_KEY trong env",
    );
  }

  return createClient(supabaseUrl, supabaseKey, {
    auth: { persistSession: false },
  });
}