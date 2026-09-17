# Workflow: visualization

## Purpose
Translate analytical findings into clear, audience-appropriate visual communication. Every chart must answer a specific question or support a specific decision.

## When to use
- User asks for a chart, plot, figure, slide, or visualization.
- Findings from analysis need to be communicated inside a report or dashboard.
- Before dashboard design (use this workflow for chart-level choices; `dashboard-ux` for layout and decision hierarchy).

Do **NOT** use:
- To "make it pretty" without first deciding what the chart must communicate.
- When a simple table or number is clearer (small cardinality, exact values required).

## Inputs
- Analytical finding or question the chart must answer.
- Audience (exec / analyst / ops / dev / external) and decision context.
- Grain, dimensions, and measures to show.
- Comparisons required (period-over-period, benchmark, target, plan, segments, scenarios).
- Output medium (report, slide, notebook, dashboard, print, mobile) and size.
- Accessibility constraints (color vision, screen reader, language).

## Preconditions
- The data is profiled: grain, outliers, nulls, extreme values, distributions known.
- The analytical question is well-formed (or created via `business-analysis` / `grill`).

## Procedure
1. **Name the question** this specific chart answers. Write it down. If you can't, stop and go back to `business-analysis`.
2. **Pick the visual form** that maps to the analysis type:
   - **Comparison (A vs B, ranked):** bar / lollipop / dot plot. Avoid pie for more than 3 slices.
   - **Trend (change over time):** line (continuous) or column (discrete periods). Confidence / uncertainty bands if applicable.
   - **Distribution (shape, spread):** histogram, KDE, boxplot, violin, ECDF. Never hide outliers without note.
   - **Relationship (two measures):** scatter (with transparency for density), hexbin, or correlation heatmap. If time-order exists, add a connecting line or facets.
   - **Composition (parts of a whole, static):** stacked bars (100% or absolute). Stacked areas only if few series and totals matter.
   - **Composition (parts of a whole, time-changing parts):** stacked area, or small multiples.
   - **Spatial:** maps only when geography materially adds to the message. Provide a table alternative if exact values matter.
   - **Single KPI:** number + delta + comparison context (target / prior / benchmark). Not a chart; prefer big-number card.
3. **Map encodings.**
   - Y axis: measure. X axis: primary dimension (time, category).
   - Color/hue: second dimension, max 5–7 levels, consistent palette across the report/dashboard.
   - Shape/text/size: use sparingly; never encode > 2–3 dimensions simultaneously.
   - Reference lines for target, baseline, or prior-period value.
4. **Visual hierarchy and annotations.**
   - Key insight (e.g., "inflection point at 2025-03" or "Region A 18% below target") called out with label, arrow, or highlighting.
   - Rank-sort bars/lines unless the natural order (time, geography) carries meaning.
   - Axis labels: descriptive with units. No bare `month` or `value`.
   - Source / grain / last-refresh footnote on every plot.
5. **Color and accessibility.**
   - Colorblind-safe palette (viridis, Okabe-Ito, Tableau 10 with care). No red-green as sole encoding.
   - 4.5:1 contrast minimum for text.
   - Use patterns + color, or facets, if encodings must be distinguishable on print/B&W.
   - Provide alt text / descriptions of the key takeaway for tooltips and screen readers.
6. **Manage cognitive load.**
   - One message per chart. Split multi-message into facets or subplots.
   - Direct labeling preferred over separate legend when possible.
   - Minimize chart junk: 3D, heavy borders, unnecessary gridlines, rotation that reads like a CAPTCHA.
7. **Validate the chart.**
   - Can the intended user answer the original question from this chart without reading surrounding text? If no, iterate.
   - Are common misreadings prevented? (Log scale labeled, dual axes avoided or clearly marked, truncated Y axis justified and visible.)
   - Spot-check the underlying data values against the chart's marks for 3–5 representative points.
8. **Storytelling layer (for reports/presentations).**
   - Order: Context → KPI → Diagnosis → Detail → Action.
   - Each chart + caption = one claim that the chart supports.

## Decision points
- If a chart conveys < 10 numbers, consider a table or a single number instead.
- If dual axes are tempting, consider faceted charts or two separate charts with aligned X axes.
- If log scale is used, state why (e.g., "log scale due to 3 orders of magnitude range") and label ticks explicitly.
- If outliers dominate visual space, show both full-scale and zoomed facets (or cap with annotation).

## Validation
- Chart directly answers the question written in Step 1.
- Grain, measure definition, and units match the business context.
- No misleading truncations, dual axes, or stacked-area-with-many-series pitfalls without explicit justification.
- Spot-check 3–5 values matches the underlying data.
- Accessibility: palette passes color-vision-safe check; labels readable at the output size.

## Expected outputs
- Chart(s) saved in appropriate format (SVG preferred for vector, PNG with explicit DPI for raster, HTML/js for interactive).
- For each chart: title, question answered, source, grain, last refresh, key takeaway, alt text.
- Interactive charts: explicit list of interactions (hover, drill, filter, tooltip fields).
- Figure captions and ordering for reports/presentations.

## Common failure modes
- Chart first, question later → pretty picture that says nothing.
- Default matplotlib / seaborn / Power BI defaults untouched: missing labels, bad palette, no context.
- Pie with 12 categories, stacked area with 15 series, 3D anything.
- Dual axes with incompatible measures → invite wrong comparisons.
- Y-axis truncated without note.
- Color only as encoder → inaccessible to ~8% of males.
- No source/freshness footnote → readers can't assess trust.

## References to load
- `references/visualization.md` — detailed chart-selection matrix, encodings, palette references, anti-patterns.
- `references/dashboard-ux.md` → after chart design, if this is part of a dashboard.
- `references/statistics.md` if visualizing uncertainty / distributions / confidence bands.

## Completion criteria
- Each chart has a named question and answers it.
- Chart type, encoding, and color are appropriate.
- Source, grain, units, last-refresh stated.
- Accessibility addressed (palette, contrast, alt text).
- Spot-checks of data values vs. chart marks pass.
- Cognitive load is low; one message per chart.
