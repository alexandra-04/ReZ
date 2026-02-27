#!/usr/bin/env python3
"""
ingest_recipe.py (adaptado a 001_initial_schema.sql)

Uso:
  python ingest_recipe.py --url "manual://spaghetti" --title "Spaghetti aglio e olio" --servings 2 \
    --ingredients-file 001_recipe.txt --platform other

Env:
  export DATABASE_URL="postgresql://ale:TU_PASSWORD@localhost:5432/recipe_cart"
"""

import argparse
import os
import sys
from typing import List, Optional


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL no está seteado. Ej: export DATABASE_URL='postgresql://.../recipe_cart'")

    import psycopg  # psycopg v3
    return psycopg.connect(db_url)


def read_ingredients(ingredients_file: Optional[str], ingredients_inline: Optional[str]) -> List[str]:
    if ingredients_file:
        with open(ingredients_file, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines()]
    else:
        lines = [ln.strip() for ln in (ingredients_inline or "").splitlines()]

    cleaned = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        ln = ln.lstrip("-•*").strip()
        if ln:
            cleaned.append(ln)
    return cleaned


def insert_recipe_and_ingredients(
    conn,
    platform: str,
    url: str,
    title: Optional[str],
    servings_base: Optional[float],
    transcript_text: Optional[str],
    raw_caption_text: Optional[str],
    ingredient_lines: List[str],
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO recipes (source_platform, source_url, title, servings_base, transcript_text, raw_caption_text)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING recipe_id
            """,
            (platform, url, title, servings_base, transcript_text, raw_caption_text),
        )
        recipe_id = cur.fetchone()[0]

        # line_order es NOT NULL, así que lo llenamos 1..n
        cur.executemany(
            """
            INSERT INTO recipe_ingredients (recipe_id, ingredient_raw, line_order)
            VALUES (%s, %s, %s)
            """,
            [(recipe_id, ln, i + 1) for i, ln in enumerate(ingredient_lines)],
        )

    conn.commit()
    return recipe_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="other", choices=["tiktok", "instagram", "youtube", "other"])
    ap.add_argument("--url", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--servings", type=float, default=None, help="Esto se guarda en recipes.servings_base")
    ap.add_argument("--transcript-text", default=None, help="Se guarda en recipes.transcript_text")
    ap.add_argument("--raw-caption-text", default=None, help="Se guarda en recipes.raw_caption_text")
    ap.add_argument("--ingredients-file", default=None)
    ap.add_argument("--ingredients", default=None)
    args = ap.parse_args()

    if not args.ingredients_file and not args.ingredients:
        print("ERROR: Debes pasar --ingredients-file o --ingredients", file=sys.stderr)
        sys.exit(1)

    ingredient_lines = read_ingredients(args.ingredients_file, args.ingredients)
    if not ingredient_lines:
        print("ERROR: No hay ingredientes para insertar", file=sys.stderr)
        sys.exit(1)

    conn = get_conn()
    try:
        recipe_id = insert_recipe_and_ingredients(
            conn=conn,
            platform=args.platform,
            url=args.url,
            title=args.title,
            servings_base=args.servings,
            transcript_text=args.transcript_text,
            raw_caption_text=args.raw_caption_text,
            ingredient_lines=ingredient_lines,
        )
        print(f"OK: inserted recipe_id={recipe_id} ingredients={len(ingredient_lines)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
