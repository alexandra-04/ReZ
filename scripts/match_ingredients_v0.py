import argparse
import re
from app.db import get_conn

STOP = {
    "g", "kg", "ml", "l", "tbsp", "tsp", "cup", "cups", "clove", "cloves",
    "pinch", "dash", "small", "large", "medium", "fresh", "ground",
    "of", "and", "or", "to", "taste"
}

def keywords(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    toks = [t for t in s.split() if t and t not in STOP]
    # usa hasta 3 tokens “más útiles” (últimos suelen ser el ingrediente)
    return " ".join(toks[-3:]) if toks else s.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipe-id", required=True)
    ap.add_argument("--retailer", default=None, help="si lo pasas, filtra products.retailer")
    ap.add_argument("--topn", type=int, default=5)
    ap.add_argument("--reset", action="store_true", help="borra matches previos auto_rules para esta receta")
    args = ap.parse_args()

    with get_conn() as conn, conn.cursor() as cur:
        if args.reset:
            cur.execute(
                """
                DELETE FROM ingredient_matches m
                USING recipe_ingredients ri
                WHERE m.recipe_ingredient_id = ri.recipe_ingredient_id
                  AND ri.recipe_id = %s
                  AND m.match_method = 'auto_rules'
                """,
                (args.recipe_id,),
            )

        cur.execute(
            """
            SELECT recipe_ingredient_id, ingredient_raw
            FROM recipe_ingredients
            WHERE recipe_id = %s
            ORDER BY line_order
            """,
            (args.recipe_id,),
        )
        rows = cur.fetchall()

        inserted = 0
        for recipe_ingredient_id, ingredient_raw in rows:
            kw = keywords(ingredient_raw)
            if not kw:
                continue

            if args.retailer:
                cur.execute(
                    """
                    SELECT product_id, name
                    FROM products
                    WHERE is_active = true
                      AND retailer = %s
                      AND name ILIKE %s
                    LIMIT %s
                    """,
                    (args.retailer, f"%{kw}%", args.topn),
                )
            else:
                cur.execute(
                    """
                    SELECT product_id, name
                    FROM products
                    WHERE is_active = true
                      AND name ILIKE %s
                    LIMIT %s
                    """,
                    (f"%{kw}%", args.topn),
                )

            candidates = cur.fetchall()

            # fallback: si no encontró nada, intenta con última palabra
            if not candidates:
                last = ingredient_raw.strip().split()[-1].lower()
                if args.retailer:
                    cur.execute(
                        """
                        SELECT product_id, name
                        FROM products
                        WHERE is_active = true
                          AND retailer = %s
                          AND name ILIKE %s
                        LIMIT %s
                        """,
                        (args.retailer, f"%{last}%", args.topn),
                    )
                else:
                    cur.execute(
                        """
                        SELECT product_id, name
                        FROM products
                        WHERE is_active = true
                          AND name ILIKE %s
                        LIMIT %s
                        """,
                        (f"%{last}%", args.topn),
                    )
                candidates = cur.fetchall()

            # inserta candidatos con score simple (rank inverso)
            for rank, (product_id, _name) in enumerate(candidates, start=1):
                score = 1.0 / rank
                cur.execute(
                    """
                    INSERT INTO ingredient_matches
                    (recipe_ingredient_id, product_id, match_method, score)
                    VALUES (%s, %s, 'auto_rules', %s)
                    """,
                    (recipe_ingredient_id, product_id, score),
                )
                inserted += 1

        conn.commit()
        print(f"OK: inserted {inserted} ingredient_matches (auto_rules)")

if __name__ == "__main__":
    main()