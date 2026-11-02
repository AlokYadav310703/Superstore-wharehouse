# """
# 05_load_to_postgres.py

# Loads the processed star-schema CSVs (produced by 02_build_dimensions.ipynb
# and 03_build_fact.ipynb) into a local PostgreSQL database.

# Prerequisites:
#     pip install psycopg2-binary sqlalchemy pandas --break-system-packages

#     1. PostgreSQL installed and running locally.
#     2. A database created, e.g.:  createdb superstore_dw
#     3. Schema created:            psql -d superstore_dw -f sql/ddl/01_create_schema.sql

# Update DB_CONFIG below with your own local Postgres credentials before running.
# """

# import pandas as pd
# from sqlalchemy import create_engine

# # ---------------------------------------------------------------------------
# # CONFIG — update with your local Postgres connection details
# # ---------------------------------------------------------------------------
# DB_CONFIG = {
#     "user": "postgres",
#     "password": "4268superstore-data-warehouse",
#     "host": "postgresql://postgres:4268superstore-data-warehouse@db.ushebqpusopniqqzgonf.supabase.co:5432/postgres",   # from Supabase dashboard
#     "port": "5432",
#     "database": "postgres",                    # Supabase's default db name
# }

# DATA_DIR = "../data/processed"

# # Load order matters: dimensions before the fact table, since fact_sales
# # has foreign key constraints pointing at all four dimensions.
# LOAD_ORDER = ["dim_customer", "dim_product", "dim_location", "dim_date", "fact_sales"]

# DATE_COLUMNS = {
#     "dim_customer": ["effective_date", "end_date"],
#     "dim_date": ["full_date"],
# }


# def get_engine():
#     url = (
#         f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
#         f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
#     )
#     return create_engine(url)


# def load_table(engine, table_name: str):
#     csv_path = f"{DATA_DIR}/{table_name}.csv"
#     print(f"\nLoading {csv_path} -> {table_name}")

#     df = pd.read_csv(csv_path)

#     for col in DATE_COLUMNS.get(table_name, []):
#         df[col] = pd.to_datetime(df[col]).dt.date

#     # Postal Code must stay a zero-padded string, not get reinterpreted as a number
#     if table_name == "dim_location":
#         df["Postal Code"] = df["Postal Code"].astype(str).str.zfill(5)

#     df.to_sql(
#         table_name,
#         engine,
#         if_exists="append",   # table + constraints already created by the DDL script
#         index=False,
#         method="multi",       # batches inserts — much faster than row-by-row
#         chunksize=1000,
#     )

#     with engine.connect() as conn:
#         result = conn.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"')
#         row_count = result.scalar()

#     print(f"Loaded {row_count} rows into {table_name} ({len(df)} rows in source CSV)")
#     if row_count != len(df):
#         print(f"  WARNING: row count mismatch for {table_name}!")


# def main():
#     engine = get_engine()
#     for table_name in LOAD_ORDER:
#         load_table(engine, table_name)
#     print("\nAll tables loaded into Postgres.")


# if __name__ == "__main__":
#     main()
"""
05_load_to_postgres.py

Loads the processed star-schema CSVs (produced by 02_build_dimensions.ipynb
and 03_build_fact.ipynb) into a local PostgreSQL database.

Prerequisites:
    pip install psycopg2-binary sqlalchemy pandas --break-system-packages

    1. PostgreSQL installed and running locally.
    2. A database created, e.g.:  createdb superstore_dw
    3. Schema created:            psql -d superstore_dw -f sql/ddl/01_create_schema.sql

Update DB_CONFIG below with your own local Postgres credentials before running.
"""

import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus

# ---------------------------------------------------------------------------
# CONFIG — update with your local Postgres connection details
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "user": "postgres.ushebqpusopniqqzgonf",
    "password": "4268superstore-data-warehouse",
    "host": "aws-0-ap-northeast-1.pooler.supabase.com",
    "port": "5432",
    "database": "postgres",
}

DATA_DIR = "../data/processed"

# Load order matters: dimensions before the fact table, since fact_sales
# has foreign key constraints pointing at all four dimensions.
LOAD_ORDER = ["dim_customer", "dim_product", "dim_location", "dim_date", "fact_sales"]

DATE_COLUMNS = {
    "dim_customer": ["effective_date", "end_date"],
    "dim_date": ["full_date"],
}


def get_engine():
    # URL-encode user/password — required if either contains characters like
    # @, :, /, or # (common in generated Supabase passwords), which would
    # otherwise break the connection string and get misparsed (e.g. an empty
    # port, as in the ValueError this caused before this fix).
    user = quote_plus(DB_CONFIG["user"])
    password = quote_plus(DB_CONFIG["password"])

    url = (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(url)


def load_table(engine, table_name: str):
    csv_path = f"{DATA_DIR}/{table_name}.csv"
    print(f"\nLoading {csv_path} -> {table_name}")

    df = pd.read_csv(csv_path)

    for col in DATE_COLUMNS.get(table_name, []):
        df[col] = pd.to_datetime(df[col]).dt.date

    # Postal Code must stay a zero-padded string, not get reinterpreted as a number
    if table_name == "dim_location":
        df["Postal Code"] = df["Postal Code"].astype(str).str.zfill(5)

    df.to_sql(
        table_name,
        engine,
        if_exists="append",   # table + constraints already created by the DDL script
        index=False,
        method="multi",       # batches inserts — much faster than row-by-row
        chunksize=1000,
    )

    with engine.connect() as conn:
        result = conn.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = result.scalar()

    print(f"Loaded {row_count} rows into {table_name} ({len(df)} rows in source CSV)")
    if row_count != len(df):
        print(f"  WARNING: row count mismatch for {table_name}!")


def main():
    engine = get_engine()
    for table_name in LOAD_ORDER:
        load_table(engine, table_name)
    print("\nAll tables loaded into Postgres.")


if __name__ == "__main__":
    main()