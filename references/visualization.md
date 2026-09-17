# Data Visualization Reference Guide

## When Used
Data visualization is the **primary output channel** of analytics. Apply visualization principles when:
- Communicating data-driven insights to executives, managers, or frontline teams
- Building interactive Power BI / Tableau / Looker dashboards used daily
- Exploring data during analysis (histograms, scatter, boxplots to understand distributions)
- Publishing reports, board decks, or infographics to external stakeholders
- Detecting anomalies, trends, seasonal patterns, outliers in time-series
- Communicating uncertainty (forecast bands, CIs) to prevent false confidence
- Telling a data story with a clear beginning → middle → conclusion

## When NOT Used
- **Transmitting exact 10-digit financial figures for accounting reconciliation** — use a table.
- **Raw data dumps (30 columns × 1000 rows) without summarization** — export to Excel/CSV as a table; not a chart.
- **A decision that is politically sensitive and will be distorted by framing** — pair charts with robust written methodology, tables, and source links.
- **Pure aesthetic data art / dashboards that nobody reads** — every dashboard needs a decision it supports; if a chart doesn't drive an action, delete it.
- **Legal / compliance disclosures requiring exact reproducibility from a static PDF** — use a data appendix table, not a plot.
- **A live-updating dashboard with more than 20 visuals on one page** — cognitive overload; split into focused pages per persona.

---

## Common Mistakes

1. **3D pie charts, 3D bar charts, pseudo-3D anything** — perspective distorts perception of relative size; 30% slice looks 15% smaller than a 2D slice. Ban 3D entirely.
2. **Dual Y-axes with different scales (lines + bars on left/right)** — viewers unconsciously compare the heights; manipulate the scale and any story can be told. Use small multiples or indexed charts instead.
3. **Pie chart with ≥ 5 slices** — human eye cannot reliably rank non-adjacent wedges beyond 3–4. Switch to bar chart (horizontal, sorted).
4. **"Chart junk"**: heavy gridlines, decorative backgrounds, drop-shadows, 3D effects, unnecessary logos, bevels, gradient fills.
5. **Not starting a bar chart at zero.** The bar's *length* encodes magnitude; truncating exaggerates differences (e.g., €4M vs €6M with y-axis starting at €3.5M → bar looks 4× taller, actual difference 50%). Line charts *may* zoom; bar charts never.
6. **Color-encoding without consideration for color-blindness** (≈8% of men, red-green CVD). Use Viridis/ColorBrewer color-safe palettes; pair color with pattern/text label.
7. **Ordering categories alphabetically** in bar charts instead of by value → cognitive overhead for the reader; sort descending (or ascending) by metric.
8. **Missing chart titles, units, axis labels, data sources.** A chart without units is meaningless ("Revenue was 42" — 42 what? euros? dollars? millions?).
9. **Over-plotting in scatter plots** with 500k points → a black blob. Use hexbin, 2D histograms, sample + jitter, or density contours.
10. **Putting too much in one chart** (10 lines = spaghetti plot). Use small multiples (one line per sub-chart) or interactive filtering.
11. **Inconsistent date formatting** (some charts MM/DD, others DD/MM) in the same dashboard → viewers misread time periods.
12. **Cherry-picking axes ranges or time windows** to make a point (showing 3 months of growth since the lowest trough, omitting 2 years of prior decline).
13. **"Because we can" charts**: word clouds, donut charts (readability worse than pie), radar/spider charts (area misleads, hard to compare axes), gauge charts (tiny data density → use a KPI card + target bar instead).
14. **No annotation of events.** A revenue dip on strike-day without a callout → viewers invent explanations.

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Static image (PNG/PDF) vs Interactive dashboard** | Static: embeddable in slide decks, reproducible, works offline, no rendering bugs. Interactive: drill-through, filter, self-service, tooltip detail. | Static: one chart per slice; no ad-hoc exploration. Interactive: requires BI tool / web browser; slower; users may misinterpret filters. |
| **Table vs Chart** | Table: exact numbers, best for financials, auditable. Chart: spot trends/outliers, communicate magnitude/shape quickly. | Table: "can't see the forest for the trees"; no pattern recognition at scale. Chart: loses 2–3 significant digits of precision. |
| **Line vs Bar for time-series** | Line: continuous, shows trend + seasonality over many periods. Bar: emphasizes discrete period totals; OK for ≤24 months. | Line for discrete categorical comparison = meaningless. Bar for 100+ periods = dense/unreadable. |
| **Same-axis overlay vs Small multiples** | Overlay: direct visual comparison of lines, shared scale, compact. Small multiples (faceted): one per group → avoids spaghetti; each trend clear. | Overlay > 5 lines → spaghetti. Small multiples: harder to compare line heights across far-apart panels. |
| **Heatmap vs Scatter** | Heatmap: density readable even for 10M rows; pattern of regions clear. Scatter: shows outliers, exact coordinates of individual points. | Heatmap: aggregates, hides outliers. Scatter: overplotting at > 10k points; becomes useless. |
| **Color hue vs Position vs Length (encoding magnitude)** | Length (bars): *most* accurate perceptual encoding (±1%). Position (scatter): next best. Hue/color: *least* accurate; qualitative, avoid for numeric magnitude. | Using color to encode 50 shades of magnitude → readers can't rank correctly. |
| **Matplotlib/Seaborn vs Plotly/Altair vs Power BI visuals** | Matplotlib: publication quality, fine-grained control, vector output. Plotly/Altair: interactive, tooltips, web-native, hover. PBI visuals: dataset-integrated, slicer cross-filter, zero deployment. | Matplotlib: static-only, verbose API. Plotly: heavier files, JS rendering issues in email. PBI: limited custom formatting; proprietary. |
| **One dashboard page with slicers vs Multi-page focused story** | Single page: convenience for exec; all KPIs at a glance. Multi-page: per-audience focus, lower cognitive load, per-page drill-down narrative. | Single page: performance + cognitive overload. Multi-page: navigation friction; users miss hidden insights. |

---

## Chart Selection (Decision Tree)

Use the **"What are you trying to show?"** test:

| Goal | Recommended Chart(s) | Avoid |
|------|---------------------|-------|
| **Compare discrete categories (A vs B vs C)** | Horizontal bar (sorted), Lollipop chart, Dot plot with error bars. Vertical bar if ≤ 8 cats. | Pie if > 4 cats, Donut, 3D bar. |
| **Show composition / parts-of-a-whole** | Stacked bar (≤5 segments), Stacked area (time composition), Treemap (hierarchical, 10–50 items). **Pie/donut ONLY if ≤3 slices and labels placed inside wedges.** | Pie with ≥ 5 slices; donut with ≥ 4 slices; Waffle chart (pretty but low data density). |
| **Trend / change over time (continuous)** | Line chart (primary), Indexed line chart (100 = baseline), Area chart if only 1 series or stacked composition. Smoothed LOESS line if noisy raw data points. | Bar chart for 100+ time periods; line chart with ≤ 5 points. |
| **Distribution of a continuous variable** | Histogram (bins), Box plot (quartiles + outliers), Violin plot + box overlay, ECDF (empirical cumulative distribution — underused but most information). Rug plot for N ≤ 500. | Bar chart with arbitrary bin widths; density curve without showing data points. |
| **Relationship between 2 continuous variables** | Scatter plot (+ jitter for discrete), Bubble for 3rd variable (size encodes), Hexbin / 2D histogram for >10k points. Scatter + linear trend line + 95% CI shade. | 3D scatter; connecting lines between unrelated points. |
| **Relationships with ≥ 3 variables** | Scatter plot matrix / Pairplot, Faceted small multiples, Parallel coordinates (for ≥ 5 continuous dims). Heatmap of correlation matrix. | Radar / spider charts; too many encoding channels in one plot. |
| **Ranking (Top 10 / Bottom 10)** | Horizontal bar (sorted), Lollipop with highlight on Top3, Slope chart (ranking change between two periods). | Alphabetically-sorted bars; tables. |
| **Geographic / spatial** | Choropleth (if normalized per-capita, not raw counts), Dot-density map, Tile grid map (equal-area by region to avoid pop-bias). | Choropleth with raw absolute counts → populous regions always "win"; bubble on top of choropleth for absolute values. |
| **Uncertainty / forecasting** | Line + shaded 80% / 95% prediction interval; Fan charts; Box plot per forecast horizon. Error bars on bar charts (± 1 SE or ± 95% CI). | Point forecast alone without any interval; truncated error bars. |
| **KPI single number** | Big-number KPI card + sparkline trend in background + delta indicator (↑ ↓ vs PY / target). Donut gauge; 3D meters with huge color range. | |
| **Correlation matrix / many-to-many** | Correlation heatmap (diverging palette centered at 0), Hierarchically-clustered heatmap with dendrogram. | Table of 30×30 r-values. |
| **Flow / Sankey** | Sankey diagram (paths from source → sink), Alluvial (changes over time cohorts). Strictly for flows between stages, never for ranking. | Stacked bar mis-representing flow. |

---

## Visual Hierarchy & Storytelling

### Design Principles
1. **Inverted pyramid** — Most important KPI top-left (where eyes land first). Supporting trends middle; drill-through tables bottom-right.
2. **Gestalt principles:**
   - **Proximity** → items near each other are perceived as related (group related KPIs with whitespace).
   - **Similarity** → same color = same semantic meaning (e.g., "Actual" is always teal, "Forecast" is always dashed grey).
   - **Enclosure** → a light card around 3 related revenue charts = user treats them as a set.
3. **Consistency across pages** — same color per category, same date format, same number formatting per measure, same legend position.
4. **Annotation as the story.** Add callouts:
   - "⬇ Strike action 14–18 March"
   - "⬆ New pricing launched Q3"
   - "↓ Dummy entry test flagged; corrected in v2"
5. **Cognitive load < 7 chunks per page.** Miller's law: working memory ≈ 7 items. If a dashboard page has > 15 visuals, ½ are ignored. Split into multiple pages.

### Color Accessibility (WCAG 2.1 AA — Minimum Bar)
- **Text contrast ≥ 4.5:1** for normal text; ≥ 3:1 for large text. Test with WebAIM Contrast Checker.
- **Don't rely on color alone.** Always pair color difference with shape/pattern/text label:
  - Solid line for Actual, dashed for Forecast (not just blue vs orange).
  - In Power BI conditional formatting: color + icon + data label together.
- **Use CVD (color vision deficiency) safe palettes:**
  - Sequential continuous: Viridis, Plasma, Inferno, Magma, Cividis (matplotlib defaults). Never use "Jet" rainbow.
  - Diverging: RdBu, Purple-Green, Blue-Orange (ColorBrewer).
  - Qualitative (≤ 8 categories): Okabe-Ito palette, Tableau 10, or `seaborn.color_palette("colorblind")`.
- **Always run a CVD simulation** (Coblis, Color Safe, or Power BI "View → Color blind filters").
- **Avoid pure red + pure green** adjacent pairs; 8% of men cannot distinguish.

### Labeling Rules
- **Every chart:** Title (what + when + where), subtitle (caveat), source line ("Source: SAP ECC via dbt mart, 2024-09-17 refresh, UTC+1").
- **Y-axis:** Label with units (€ Millions, % of customers, Count per day).
- **X-axis:** No tilted 45° labels (unreadable); rotate chart to horizontal bars if category labels are long.
- **Bars/Lines:** Direct label the endpoint of each line (when ≤ 5 lines) instead of a separate legend. Removes eye movement.
- **Units** — Abbreviate consistently: k, M, B or thousand, million, billion. Never mix k (kilo) and K (Kelvin) in same report.

---

## Good Implementation

### Matplotlib + Seaborn (Publication Style, Accessible)

```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import numpy as np
import pandas as pd

# Global style — set ONCE per project, never per chart
sns.set_theme(
    style="whitegrid",
    context="talk",
    palette="colorblind",          # CVD-safe qualitative palette
    font="Segoe UI",
    font_scale=1.05,
)
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "axes.labelpad": 10,
    "axes.titlepad": 18,
    "legend.frameon": False,
    "legend.loc": "upper left",
})

def plot_revenue_trend_with_forecast(df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Historical line
    hist = df[df["type"] == "actual"]
    ax.plot(hist["month"], hist["revenue_meur"],
            color="#1f77b4", linewidth=2.2, label="Actual revenue")

    # Forecast + uncertainty band
    fc = df[df["type"] == "forecast"]
    ax.plot(fc["month"], fc["revenue_meur"],
            color="#1f77b4", linewidth=2, linestyle="--", label="Forecast (P50)")
    ax.fill_between(fc["month"], fc["revenue_p10"], fc["revenue_p90"],
                    color="#1f77b4", alpha=0.15, label="Forecast P10–P90 band")

    # Annotations
    ax.annotate("New pricing launch",
                xy=("2024-07-01", df.loc[df.month=="2024-07-01", "revenue_meur"].iloc[0]),
                xytext=(30, 30), textcoords="offset points",
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#555"),
                fontsize=11, color="#333")

    # Axes
    ax.set_title("Revenue actual & forecast, 2023–2025, monthly")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (M€)")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.axhline(0, color="#999", lw=0.7)

    # Minimal grid, light
    ax.grid(axis="y", alpha=0.25)
    ax.grid(axis="x", alpha=0.0)

    ax.legend(ncol=3, bbox_to_anchor=(0, 1.02), loc="lower left")

    # Mandatory: source, refresh date, methodology line
    fig.text(0.99, 0.01, "Source: mart_sales_monthly, refreshed 2024-09-17 | Forecast: ARIMA(2,1,1)×(1,1,0)[12]",
             ha="right", va="bottom", fontsize=9, color="#666")
    return fig
```

### Plotly (Interactive Dashboard / HTML Embedding)

```python
import plotly.express as px

fig = px.bar(
    df_top10.sort_values("revenue", ascending=True),
    x="revenue", y="customer_name",
    orientation="h",
    color="segment",
    color_discrete_sequence=px.colors.qualitative.Safe,  # CVD-safe
    title="Top 10 customers by revenue YTD 2024",
    labels=dict(revenue="Revenue (€)", customer_name="Customer", segment="Segment"),
    hover_data={"country": True, "orders": ":,.0f", "revenue": ":,.2f €"},
    text_auto=".2s",
)
fig.update_layout(
    height=520,
    showlegend=True,
    plot_bgcolor="white",
    xaxis=dict(gridcolor="#eee", title=dict(font=dict(size=13))),
    yaxis=dict(title=None),
    margin=dict(l=10, r=10, t=60, b=60),
)
fig.add_annotation(
    x=1, y=-0.18, xref="paper", yref="paper",
    text="Source: mart_sales_customer_ytd, refresh 2024-09-17",
    showarrow=False, font=dict(color="#888", size=11), xanchor="right"
)
fig.show()
```

### Power BI Dashboard Page Blueprint (5–8 visual max)

```
[Top Row — 3 KPI cards: Revenue MTD, Orders MTD, Return Rate %]
   ├─ Each card: Big number, small sparkline trend last 13 periods, YoY% delta triangle.
   └─ Green/red only on delta, never on absolute.

[Middle Left — Line chart]
   ├─ Revenue (actual, solid) + Forecast (dashed) + PY (light, dotted), monthly last 2 years.
   └─ Shared Y-axis zero baseline; annotation callouts on events.

[Middle Right — Horizontal bar top 10 countries]
   └─ Sorted desc; direct label end of bar; hide legend (label on bar directly).

[Bottom Left — Stacked column composition by segment, monthly]
   └─ Legend at top; only 5 segments; use consistent CVD-safe qualitative palette.

[Bottom Right — Scatter: Discount % vs Return Rate per product]
   └─ Bubble size by revenue; reference line at global avg return rate; quadrant highlight.
```

---

## How to Test a Visualization

1. **Send a screenshot + question to a non-expert.** "What is the revenue for France in August?" If they can't answer in < 3 seconds, chart is broken.
2. **Remove the legend; can readers still identify which series is which?** If not, use direct labels.
3. **CVD simulator** (Coblis or Power BI colorblind view): are "Target" and "Actual" still distinguishable in protanopia/deuteranopia?
4. **Black-and-white print test** → if all lines print as indistinguishable black, add markers/line styles.
5. **Mobile rendering test** → do lines/axis labels get cut off; is KPI text readable on a phone?
6. **Accessibility screenreader (NVDA/JAWS)** → alt-text on each visual reads "Chart: Revenue line chart from Jan 2023 to Aug 2024; peak €14.2M in Nov 2023; current €12.8M Aug 2024."
7. **Unit tests for statistical visuals** (pytest + matplotlib image-comparison):
   ```python
   from matplotlib.testing.decorators import check_figures_equal
   def test_revenue_plot_matches_golden():
       fig = plot_revenue_trend_with_forecast(fixture_df)
       # compare vs committed PNG baseline, tolerance per-pixel
   ```
8. **Dashboard user research with target audience** — 5 users doing 3 defined tasks (find YoY%, filter by Germany, drill to customer) → task success rate ≥ 90%.

---

## Performance Behavior

| Tool / Pattern | Load Latency Typical | Notes |
|---------------|----------------------|-------|
| Matplotlib PNG (vector-free) | 50–500 ms render; file 50–500 KB | Always save SVG for print-quality editors; PNG for email. |
| Plotly figure with 10 series × 1000 points | 50–200 ms first render; 1–5 MB HTML | Aggregate to ≤ 1000 points in browser; use `scattergl` for 100k+ points (WebGL). |
| Power BI line chart × 5 series | 50–200 ms interactive; refresh tied to dataset | If > 10,000 data points rendered, aggregate in DAX to month-level first. |
| Power BI map (filled choropleth + 10k geocodes) | 500 ms–3 s | Use Azure Maps or reduce to region level. |
| Seaborn heatmap 100×100 | 50–200 ms | 1000×1000 → render with matplotlib `imshow`; use Seaborn only for small heatmaps. |
| Hexbin 1M rows (Matplotlib) | 200–500 ms | Better than scatter for density; no overplotting. |
| Dashboard with 25 Power BI visuals | 2–10 s; DAX recalc on every slicer click | 5–8 visuals/page target; use drill-through not everything-on-one-page. |

---

## What to Inspect First (Chart Misleads / Fails)

1. **Does a bar chart have a non-zero baseline?** → Fix immediately; only lines may zoom; bars may never.
2. **Axes units defined?** → "k€" vs "M$" ambiguity = chart is meaningless.
3. **Color + only color coding difference?** → Add shape/pattern/label if CVD.
4. **Dual Y-axis?** → Replace with indexed, small multiples, or 2 separate aligned subplots.
5. **Unsorted categories?** → Sort by magnitude unless a natural temporal/categorical order exists (month name order, maturity stage).
6. **Data source & date missing?** → Readers can't trust; add footer.
7. **Chart-junk (gridlines, colors, borders)?** → Remove any line/color not encoding data (Tufte: maximize data-ink ratio).
8. **Event annotations missing on anomalies?** → If readers have to *guess* what happened in Q2, you failed.
9. **Pie/donut with 6+ slices?** → Replace with horizontal bar.
10. **Line chart has > 7 lines (spaghetti)?** → Facet to small multiples, or use interactive hover + highlight only the selected one.

---

## Caveats & Common Chart Pitfalls

- **Beware of baseline comparisons to "best-ever month."** You'll always be down 20%; compare to trailing 3-year average for the same month or same-period-last-year.
- **Choropleths lie by population.** Always normalise by population/denominator (revenue per capita, churn rate) not raw absolute revenue.
- **Log-scale axes without explicit warning** → a 45° line on log-scale chart is exponential growth, not linear. Always label "Y-axis (log10 scale)."
- **Survivorship bias.** Revenue of "current top 10 products" over last 5 years is inflated — products that were discontinued are excluded. Use a consistent cohort.
- **Aggregation bias / Ecological fallacy.** Average region income vs region churn correlation may not hold at individual level (Simpson).
- **Moving average with 12-month window on a 13-month chart** → only 2 data points; readers think they see a trend.
- **% Change on % metrics** (e.g., Return rate went from 2% to 3% = "+50%!" vs "+1 percentage point"). Always state both.
