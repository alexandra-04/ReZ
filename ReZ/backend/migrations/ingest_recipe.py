#!/usr/bin/env python3
"""
ingest_recipe.py
Uso:
  python ingest_recipe.py --url "https://..." --title "Pasta" --servings 2 --ingredients-file ingredients.txt
O:
  python ingest_recipe.py --url "manual" --title "Pasta" --servings 2 --ingredients "2 eggs\n200g flour\nsalt"

Requisitos:
  pip install psycopg[binary]  (psycopg v3)  o  pip install psycopg2-binary
Config por env vars:
  DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
  o PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD
"""

import argparse
import os
import sys
from typing import List, Optional


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    try:
        import psycopg  # psycopg v3
        if db_url:
            return psycopg.connect(db_url)
        return psycopg.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
        )
    except ImportError:
        import psycopg2  # type: ignore
        if db_url:
            return psycopg2.connect(db_url)
        return psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
        )


def read_ingredients(args) -> List[str]:
    if args.ingredients_file:
        with open(args.ingredients_file, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines()]
    else:
        lines = [ln.strip() for ln in (args.ingredients or "").splitlines()]

    # limpia líneas vacías / bullets típicos
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
    url: str,
    title: str,
    servings: Optional[int],
    raw_text: Optional[str],
    ingredient_lines: List[str],
):
    # Ajusta nombres de columnas si tu schema difiere.
    # Si tu tabla recipes/ingredients usa otros nombres, dime y lo adapto.
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO recipes (source_url, title, servings, raw_text)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (url, title, servings, raw_text),
        )
        recipe_id = cur.fetchone()[0]

        cur.executemany(
            """
            INSERT INTO ingredients (recipe_id, raw_line)
            VALUES (%s, %s)
            """,
            [(recipe_id, ln) for ln in ingredient_lines],
        )

    conn.commit()
    return recipe_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--servings", type=int, default=None)
    ap.add_argument("--raw-text", default=None, help="Texto completo de la receta (opcional)")
    ap.add_argument("--ingredients-file", default=None, help="Archivo .txt con ingredientes, 1 por línea")
    ap.add_argument("--ingredients", default=None, help="Ingredientes pegados (separados por saltos de línea)")
    args = ap.parse_args()

    if not args.ingredients_file and not args.ingredients:
        print("ERROR: Debes pasar --ingredients-file o --ingredients", file=sys.stderr)
        sys.exit(1)

    ingredient_lines = read_ingredients(args)
    if not ingredient_lines:
        print("ERROR: No hay ingredientes para insertar", file=sys.stderr)
        sys.exit(1)

    conn = get_conn()
    try:
        recipe_id = insert_recipe_and_ingredients(
            conn=conn,
            url=args.url,
            title=args.title,
            servings=args.servings,
            raw_text=args.raw_text,
            ingredient_lines=ingredient_lines,
        )
        print(f"OK: inserted recipe_id={recipe_id} ingredients={len(ingredient_lines)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
