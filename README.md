# Superstore Data Warehouse

An end-to-end data modeling project that transforms the flat Superstore Sales
dataset into a proper star schema — with SCD Type 2 history tracking on the
customer dimension — loaded into PostgreSQL (Supabase) and visualized in an
interactive Power BI dashboard.

## Business Question

**Where is Superstore's revenue coming from, where is it underperforming
operationally, and how did the SCD2-tracked customer segment changes affect
their spending behavior?**

This splits into three sub-questions, each answered by its own dashboard page:
1. **Where** is revenue strongest/weakest across regions, categories, and time?
2. **How** do customer segments differ in spend, and what happens to a
   customer's behavior when their segment changes over time?
3. **How well** is the business shipping orders — which modes/regions are
   slow, and does order size affect delivery speed?

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python (pandas, numpy) |
| Data modeling / ETL | Jupyter notebooks |
| Database | PostgreSQL (hosted on Supabase) |
| Visualization | Power BI |
| Alternative warehouse (optional) | Google BigQuery |

## Dataset

Source: [Sample Superstore dataset (Kaggle)](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final)
— ~9,800 order-line records, 2015–2018, with customer, product, location, and
shipping details.

## Star Schema Design

```
                    ┌──────────────┐
                    │  dim_date    │
                    └──────┬───────┘
                           │
┌──────────────┐   ┌───────┴────────┐   ┌────────────────┐
│ dim_customer  ├───┤  fact_sales    ├───┤  dim_product    │
│  (SCD Type 2) │   │                │   │                 │
└──────────────┘   └───────┬────────┘   └────────────────┘
                           │
                    ┌──────┴───────┐
                    │ dim_location │
                    └──────────────┘
```

**Grain of `fact_sales`:** one row per order line item.

| Table | Description |
|---|---|
| `fact_sales` | Order-line facts: `Sales`, `shipping_delay`, FKs to all 4 dimensions, degenerate dimension `Ship Mode` |
| `dim_customer` | Customer ID, Name, Segment — **SCD Type 2**: `effective_date`, `end_date`, `is_current` |
| `dim_product` | Product ID, Name, Category, Sub-Category — keyed on a composite natural key (see below) |
| `dim_location` | City, State, Region, Postal Code |
| `dim_date` | Generated calendar table (day/month/quarter/year/weekday) |

### Key design decisions

- **`Product ID` is not a safe natural key.** EDA found 32 of 1,861 Product
  IDs reused across genuinely different products (same ID, different name —
  Category/Sub-Category matched coincidentally). `dim_product` is deduplicated
  on a composite natural key (`Product ID + Product Name`) instead, then
  assigned a clean surrogate `product_key`.
- **City/State/Region are order-level, not customer-level.** EDA showed 779
  of 793 customers had more than one City across their orders — confirming
  these are shipping attributes of the *order*, not a fixed attribute of the
  *customer*. They live in `dim_location`, linked to `fact_sales`
  independently of `dim_customer`.
- **`Segment` is the SCD Type 2 attribute on `dim_customer`.** EDA confirmed
  `Customer ID → Customer Name` and `Customer ID → Segment` are both true 1:1
  mappings in the source data, making Segment a genuine, stable customer
  attribute worth tracking historically. A change scenario was simulated for
  3 sample customers (segment change effective 2017-06-01) to demonstrate the
  pattern; `fact_sales.customer_key` resolves to the correct historical
  version by matching each order's date against `[effective_date, end_date]`.
- **Postal Code data quality fix.** 11 rows (all Burlington, VT) had missing
  Postal Code; imputed with the correct ZIP (05401) and zero-padded to 5
  digits to fix a leading-zero-drop bug from float conversion.

## Project Structure

```
superstore-data-warehouse/
├── data/
│   ├── raw/                    # Original Kaggle CSV (not committed)
│   └── processed/              # Cleaned dim/fact CSVs, ready to load
├── notebooks/
│   ├── 01_eda.ipynb            # Exploratory analysis, data quality findings
│   ├── 02_build_dimensions.ipynb  # Builds all 4 dimension tables + SCD2
│   └── 03_build_fact.ipynb     # Resolves SCD2 customer_key, builds fact_sales
├── sql/
│   ├── ddl/
│   │   └── 01_create_schema.sql   # PostgreSQL DDL for the star schema
│   └── queries/                # Analytical queries validated against the schema
├── etl/
│   ├── 04_load_to_bigquery.py  # Optional: load into BigQuery
│   └── 05_load_to_postgres.py  # Load into PostgreSQL / Supabase
├── docs/
│   └── design_decisions.md     # Full write-up of modeling decisions
├── outputs/                    # Dashboard screenshots, benchmark results
└── README.md
```

## Setup

1. **Download the dataset** from Kaggle and place the CSV in `data/raw/`.
2. **Run the notebooks in order:**
   - `notebooks/01_eda.ipynb`
   - `notebooks/02_build_dimensions.ipynb`
   - `notebooks/03_build_fact.ipynb`

   This produces 5 processed CSVs in `data/processed/`: `dim_customer`,
   `dim_product`, `dim_location`, `dim_date`, `fact_sales`.
3. **Create the database schema:**
   ```bash
   psql -d your_database -f sql/ddl/01_create_schema.sql
   ```
4. **Load the data:**
   ```bash
   cd etl
   python 05_load_to_postgres.py
   ```
5. **Connect Power BI** to the database (PostgreSQL connector, Import mode)
   and load all 5 tables.

## Power BI Dashboard

Three pages, each answering one part of the business question:

| Page | Focus | Key visuals |
|---|---|---|
| **Executive Overview** | Overall sales performance | KPI cards (Total Sales, Orders, Customers, AOV, Shipping Delay) w/ YoY sparklines, sales trend, sales by region/category, top 10 products |
| **Customer & Segment** | Segment behavior + SCD2 showcase | Sales by segment, customers by region, and a dedicated chart showing the 3 SCD2-simulated customers' spend split by segment before/after their change date |
| **Operations (Shipping)** | Delivery performance | Avg shipping delay by ship mode/region, sales-vs-delay scatter, ship mode × region matrix |

Slicers: Date (between), Region, Category, Segment, Ship Mode.

## Key Findings

**Revenue**
- Total Sales across the 4-year period: **$2.26M**
- Highest-performing Region: **West** (Sales: $0.71M)
- Lowest-performing Region: **South** (Sales: $0.38M)
- Best-performing Category: **Technology**, driven mainly by Sub-Category **Phones**
- Top product by Sales: **$0.32M** *(add the product name from the Top 10
  Products table alongside this figure)*

**Trend**
- Sales trend over 2015–2018: **Growing** overall.
- Seasonal pattern: a small dip in **2016**, with sales recovering and
  continuing to grow in the following years.

**Customer & Segment**
- Segment with the highest total Sales: **Consumer**
- Segment with the highest average Sales per customer: **Corporate** — meaning
  Consumer wins on volume, but Corporate customers spend more per head.
- SCD2-simulated customers (segment change effective 2017-06-01): **pending —
  pull the before/after average Sales from the Customer & Segment page's
  comparison table.**

**Operations (Shipping)**
- Slowest Ship Mode on average: **Standard Class** (~5 days)
- Fastest Ship Mode on average: **Same Day** (~1 day)
- Region with the worst average shipping delay: **Central**
- Relationship between order value and shipping delay: **Order value affects
  shipping speed — lower-cost products tend to ship faster, while
  higher-cost products tend to ship later.**

**Overall takeaway**

Superstore's revenue grew steadily from 2015–2018, led by the **West** region
and the **Technology** category (particularly Phones) — with a brief dip in
2016 that recovered the following year. The **Consumer** segment drives the
most total revenue by volume, while **Corporate** customers are the more
valuable segment per head, suggesting a case for deeper Corporate account
investment. Operationally, the **South** region lags on revenue and the
**Central** region lags on delivery speed, and **Standard Class** shipping —
the slowest mode — is also disproportionately used for higher-value orders,
pointing to fulfillment prioritization as a concrete area to investigate
further.