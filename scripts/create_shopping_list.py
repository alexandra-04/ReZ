import argparse
from app.db import get_conn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipe-id", required=True)
    ap.add_argument("--servings", type=float, required=True)
    ap.add_argument("--retailer-preference", default=None)
    args = ap.parse_args()

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO shopping_lists (recipe_id, servings_target, retailer_preference, status)
            VALUES (%s, %s, %s, 'draft')
            RETURNING shopping_list_id
            """,
            (args.recipe_id, args.servings, args.retailer_preference),
        )
        shopping_list_id = cur.fetchone()[0]

        # para cada ingrediente, elige el mejor match auto_rules (si existe)
        cur.execute(
            """
            SELECT
              ri.recipe_ingredient_id,
              ri.ingredient_raw,
              ri.quantity,
              ri.unit,
              (
                SELECT m.product_id
                FROM ingredient_matches m
                WHERE m.recipe_ingredient_id = ri.recipe_ingredient_id
                  AND m.match_method IN ('auto_rules','auto_embedding','manual')
                ORDER BY
                  m.is_selected DESC,
                  m.score DESC NULLS LAST,
                  m.created_at DESC
                LIMIT 1
              ) AS product_id
            FROM recipe_ingredients ri
            WHERE ri.recipe_id = %s
            ORDER BY ri.line_order
            """,
            (args.recipe_id,),
        )
        rows = cur.fetchall()

        for recipe_ingredient_id, ingredient_raw, qty, unit, product_id in rows:
            # item_label obligatorio
            item_label = ingredient_raw

            # si hay product_id, trae url del producto (opcional)
            product_url = None
            if product_id:
                cur.execute("SELECT product_url FROM products WHERE product_id=%s", (product_id,))
                product_url = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO shopping_list_items
                (shopping_list_id, recipe_ingredient_id, product_id, item_label, quantity, unit, product_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (shopping_list_id, recipe_ingredient_id, product_id, item_label, qty, unit, product_url),
            )

        conn.commit()
        print(f"OK: created shopping_list_id={shopping_list_id}")

if __name__ == "__main__":
    main()