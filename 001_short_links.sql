-- Bảng lưu mapping mã ngắn -> link affiliate gốc
create table if not exists short_links (
  code text primary key,
  target_url text not null,
  item_id text,
  source text,              -- 'telegram' | 'zalo' | 'web' ...
  meta jsonb,                -- lưu thêm thông tin sản phẩm/hoa hồng lúc tạo link (tuỳ chọn)
  click_count integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_short_links_item_source
  on short_links (item_id, source);

-- Bảng log từng lượt click (phục vụ thống kê / đối soát sau này)
create table if not exists short_link_clicks (
  id bigserial primary key,
  code text not null references short_links(code) on delete cascade,
  clicked_at timestamptz not null default now(),
  ip text,
  user_agent text,
  referer text
);

create index if not exists idx_short_link_clicks_code
  on short_link_clicks (code);

-- Hàm tăng click_count an toàn khi có nhiều request đồng thời
create or replace function increment_click_count(p_code text)
returns void
language sql
as $$
  update short_links set click_count = click_count + 1 where code = p_code;
$$;

-- RLS: chặn truy cập trực tiếp từ client (anon key), chỉ service role (server) mới được đọc/ghi
alter table short_links enable row level security;
alter table short_link_clicks enable row level security;
-- Không tạo policy cho anon/authenticated -> mặc định chặn hết, chỉ service role bypass RLS.
