create table if not exists affiliate_clicks (
  id serial primary key,
  user_id integer not null references users(id),
  tracking_id varchar(128) not null unique,
  network varchar(32) not null default 'ACCESSTRADE',
  campaign_id varchar(128) not null,
  merchant varchar(128), product_url text not null, aff_link text, short_link text,
  url_origin text, utm_source varchar(128), utm_medium varchar(128),
  utm_campaign varchar(128), utm_content varchar(128), sub1 varchar(128) not null,
  sub2 varchar(128), sub3 varchar(128), sub4 varchar(128),
  status varchar(32) not null default 'CREATED', created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table if exists users add column if not exists role varchar(32) not null default 'USER';

create table if not exists affiliate_orders (
  id serial primary key, network varchar(32) not null, external_order_id varchar(128) not null,
  merchant varchar(128) not null, user_id integer references users(id), tracking_id varchar(128),
  billing jsonb, commission jsonb, status integer not null, order_pending jsonb,
  order_approved jsonb, order_reject jsonb, products_count integer, click_time timestamptz,
  sales_time timestamptz, confirmed_time timestamptz, update_time timestamptz,
  at_product_link text, utm_source varchar(128), utm_medium varchar(128),
  utm_campaign varchar(128), utm_content varchar(128), raw_data jsonb not null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(network, merchant, external_order_id)
);

create table if not exists affiliate_order_items (
  id serial primary key, affiliate_order_id integer not null references affiliate_orders(id),
  external_item_id varchar(128), campaign_id varchar(128), product_id varchar(128),
  product_name varchar(500), product_category varchar(255), product_price numeric(18,2),
  product_quantity jsonb, billing_pending jsonb, billing_approved jsonb, billing_reject jsonb,
  commission_pending jsonb, commission_approved jsonb, commission_reject jsonb,
  reason_rejected text, raw_data jsonb not null
);

create table if not exists affiliate_transactions (
  id serial primary key, network varchar(32) not null, merchant varchar(128) not null,
  transaction_id varchar(128) not null, conversion_id varchar(128), affiliate_order_id integer references affiliate_orders(id),
  user_id integer references users(id), tracking_id varchar(128), product_id varchar(128) not null,
  product_name varchar(500), product_price numeric(18,2), product_quantity numeric(18,2),
  transaction_value numeric(18,2), commission numeric(18,2), status integer not null,
  is_confirmed integer, click_time timestamptz, transaction_time timestamptz, confirmed_time timestamptz,
  update_time timestamptz, reason_rejected text, is_brand_bonus boolean, raw_data jsonb not null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(network, merchant, transaction_id, product_id)
);

create table if not exists unmatched_affiliate_orders (
  id serial primary key, network varchar(32) not null, merchant varchar(128) not null,
  external_order_id varchar(128) not null, tracking_value varchar(255), raw_data jsonb not null,
  reason text not null, resolved_at timestamptz, created_at timestamptz not null default now()
);

alter table if exists cashback_transactions add column if not exists affiliate_transaction_id integer references affiliate_transactions(id);