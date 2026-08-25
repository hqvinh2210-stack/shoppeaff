import { createClient } from "@supabase/supabase-js";

// Chỉ dùng ở server (Route Handlers) - KHÔNG import file này trong client component.
// SUPABASE_SERVICE_ROLE_KEY có quyền ghi/đọc full, không được lộ ra frontend.
const supabaseUrl = process.env.SUPABASE_URL!;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

export function getSupabaseAdmin() {
  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error("Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_ROLE_KEY trong env");
  }
  return createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });
}
