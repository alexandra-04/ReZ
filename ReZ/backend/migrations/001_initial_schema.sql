-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Recipes
CREATE TABLE recipes (
  recipe_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_platform TEXT NOT NULL CHECK (source_platform IN ('tiktok','instagram','youtube','other')),
  source_url TEXT NOT NULL UNIQUE,
  title TEXT,
  author_handle TEXT,
  language_code TEXT DEFAULT 'en',
  servings_base NUMERIC(6,2),
  transcript_text TEXT,
  raw_caption_text TEXT,
  parsed_json JSONB,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','parsed','needs_review','ready')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2) Ingredients extracted per recipe
CREATE TABLE recipe_ingredients (
  recipe_ingredient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id UUID NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
  ingredient_raw TEXT NOT NULL,
  ingredient_norm TEXT,
  quantity NUMERIC(12,4),
  unit TEXT,
  optional BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT,
  line_order INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);

-- 3) Supermarket products catalog
CREATE TABLE products (
  product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  retailer TEXT NOT NULL,                 -- e.g. tesco, sainsburys
  retailer_sku TEXT,
  name TEXT NOT NULL,
  brand TEXT,
  size_text TEXT,                         -- "250g", "6 pack", etc.
  unit_price NUMERIC(12,4),
  currency TEXT DEFAULT 'GBP',
  product_url TEXT,
  image_url TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (retailer, retailer_sku)
);

CREATE INDEX idx_products_retailer ON products(retailer);
CREATE INDEX idx_products_active ON products(is_active);

-- 4) Ingredient -> product matches (auto + manual overrides)
CREATE TABLE ingredient_matches (
  match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_ingredient_id UUID NOT NULL REFERENCES recipe_ingredients(recipe_ingredient_id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(product_id) ON DELETE SET NULL,
  match_method TEXT NOT NULL CHECK (match_method IN ('auto_embedding','auto_rules','manual')),
  score NUMERIC(6,5),
  is_selected BOOLEAN NOT NULL DEFAULT FALSE,
  selected_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_matches_recipe_ingredient ON ingredient_matches(recipe_ingredient_id);
CREATE INDEX idx_matches_selected ON ingredient_matches(is_selected);

-- 5) Shopping list (per recipe + servings target)
CREATE TABLE shopping_lists (
  shopping_list_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id UUID NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
  servings_target NUMERIC(6,2) NOT NULL,
  retailer_preference TEXT,               -- optional, could be null = best-effort
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','exported')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_shopping_lists_recipe_id ON shopping_lists(recipe_id);

-- 6) Items in shopping list (resolved to product when possible)
CREATE TABLE shopping_list_items (
  shopping_list_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shopping_list_id UUID NOT NULL REFERENCES shopping_lists(shopping_list_id) ON DELETE CASCADE,
  recipe_ingredient_id UUID REFERENCES recipe_ingredients(recipe_ingredient_id) ON DELETE SET NULL,
  product_id UUID REFERENCES products(product_id) ON DELETE SET NULL,
  item_label TEXT NOT NULL,               -- display name
  quantity NUMERIC(12,4),
  unit TEXT,
  product_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_shopping_list_items_list_id ON shopping_list_items(shopping_list_id);

-- 7) Events (analytics)
CREATE TABLE events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL CHECK (event_type IN ('recipe_submitted','recipe_parsed','list_created','list_exported','product_clicked')),
  recipe_id UUID REFERENCES recipes(recipe_id) ON DELETE SET NULL,
  shopping_list_id UUID REFERENCES shopping_lists(shopping_list_id) ON DELETE SET NULL,
  product_id UUID REFERENCES products(product_id) ON DELETE SET NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_type_time ON events(event_type, created_at DESC);
