import csv
from app.db import get_conn


def main():
    with get_conn() as conn, conn.cursor() as cur:
        with open("products_seed.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cur.execute(
                    """
                    INSERT INTO products
                    (retailer, retailer_sku, name, brand, size_text, unit_price, currency, product_url, image_url, is_active)
                    VALUES
                    (%(retailer)s, %(retailer_sku)s, %(name)s, %(brand)s, %(size_text)s, %(unit_price)s, %(currency)s, %(product_url)s, %(image_url)s, %(is_active)s)
                    ON CONFLICT (retailer, retailer_sku) DO UPDATE
                      SET name=EXCLUDED.name,
                          brand=EXCLUDED.brand,
                          size_text=EXCLUDED.size_text,
                          unit_price=EXCLUDED.unit_price,
                          currency=EXCLUDED.currency,
                          product_url=EXCLUDED.product_url,
                          image_url=EXCLUDED.image_url,
                          is_active=EXCLUDED.is_active
                    """,
                    r,
                )
        conn.commit()

    print("OK: products seeded/updated")


if __name__ == "__main__":
    main()