"""
Populates project_table and blog_post_table with the portfolio's content.

Run with:
    python seed.py

Safe to re-run: existing rows (matched by slug) are updated in place rather
than duplicated, so you can edit PROJECTS_SEED / BLOG_SEED below and just
re-run this whenever a write-up changes.

Content fields (why/how/results for projects, body for posts) are stored as
Markdown, not HTML. main.py's `| markdown` Jinja filter renders it at
request time via python-markdown. Standard Markdown passes raw HTML blocks
straight through untouched, so a pasted embed (e.g. a Plotly chart export)
can be dropped directly into a Markdown field — see the chart embed inside
ontario-energy-mix's "results" field below for a live example.

Only "ontario-energy-mix" is a real project (content pulled from its actual
README and SQL scripts on GitHub). The other four are placeholder/filler
content so the Projects page doesn't look empty while more real work gets
built out — swap or remove them whenever you have real repos to replace
them with.

Note: stats like stars/forks/language/topics are NOT stored here — main.py
already fetches those live from the GitHub API on each page view, so this
script only needs to seed the narrative fields plus tagline/stack (projects)
or title/dates/tags (posts).
"""

from main import app, db, Project, BlogPost


CHECK_ICON = (
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>'
    '<polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
)


def results_block(points: list[str]) -> str:
    """Builds the Key Findings list as raw HTML — one row per point, each
    prefixed with the site's checkmark icon. This is inserted into the
    Markdown 'results' field as a raw HTML block rather than a '- ' markdown
    list, so the bullet is exactly this icon instead of markdown's default
    list marker. Rows are newline-separated (no blank line between them) so
    Markdown treats the whole thing as one HTML block and passes it through
    untouched — same mechanism used for the chart embed below."""
    return "\n".join(f'<div class="result-item">{CHECK_ICON}<span>{point}</span></div>' for point in points)


PROJECTS_SEED = [
    # --- Real project ---------------------------------------------------
    {
        "slug": "ontario-energy-mix",
        "tagline": "Tracing Natural Gas's rising share of Ontario's electricity mix since 2015",
        "why": (
            "Ontario's electricity mix has been quietly reshaped since 2015, and Natural "
            "Gas's growing role is something I'd seen debated anecdotally without ever seeing "
            "the numbers laid out end-to-end. Having spent years assessing energy systems in "
            "the field, I wanted to apply the same rigour to a grid-scale question: is Gas "
            "becoming a permanent structural fixture of the grid, or just a temporary bridge "
            "fuel while Nuclear capacity came back online?\n"
            "\n"
            "Ontario's Nuclear Refurbishment Program (2020–2023) gave me a natural "
            "before/after window to test that question, and the demand climb starting in 2024 "
            "gave me a second, independent one. I wanted an analysis that held up under both."
        ),
        "how": (
            "Data comes from IESO's public reports — monthly generation by fuel type and "
            "monthly demand — pulled directly via a Python ingestion script using requests and "
            "xml.etree.ElementTree. The whole pipeline runs in Docker: a containerized SQL "
            "Server 2022 instance is built from scratch by Docker Compose, with T-SQL scripts "
            "creating the schema, loading the CSVs, and running data-integrity checks before "
            "any analysis touches the data.\n"
            "\n"
            "Once the data was validated, the heavy lifting — 12-month rolling averages, "
            "year-over-year fuel share, and peak-demand segmentation — was done in T-SQL using "
            "window functions and CTEs. Results were pulled into a Jupyter notebook for the "
            "final analysis and visualised with Plotly and Seaborn."
        ),
        "results": (
            results_block([
                "Demand entered a sharp structural climb starting in 2024, breaking years of relative stability",
                "Gas absorbed essentially all of this growth — total generation rose 1,138 GWh from Jan 2024 to May 2026, while Gas output alone rose 1,232 GWh",
                "Gas covered most of the output lost during the 2020–2023 Nuclear Refurbishment Program, when Nuclear output fell 1,387 GWh against a total system drop of just 251 GWh",
                "Gas's share of generation rises sharply with demand stress — from 7.8% in low-demand months to as much as 18.0% in the five most extreme peak months",
            ])
            + "\n\n"
            # Raw HTML embed pasted straight from the notebook's Plotly export.
            # Markdown passes this block through untouched — no escaping, no
            # separate "chart" field needed. Sized via the .chart-embed CSS
            # class (responsive aspect-ratio box) instead of the fixed
            # pixel max-height/max-width the notebook export shipped with.
            + "<div class=\"chart-embed\">                        <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>"
        """<script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="eab3d5a8-0d5c-4373-bf73-56277471f626" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("eab3d5a8-0d5c-4373-bf73-56277471f626")) {                    Plotly.newPlot(                        "eab3d5a8-0d5c-4373-bf73-56277471f626",                        [{"fillpattern":{"shape":""},"hovertemplate":"\u003cb\u003e%{y:.2f} %\u003c\u002fb\u003e","legendgroup":"Gas","line":{"color":"#D92525"},"marker":{"symbol":"circle"},"mode":"lines","name":"Gas","orientation":"v","showlegend":true,"stackgroup":"1","x":{"dtype":"i2","bdata":"3wfgB+EH4gfjB+QH5QfmB+cH6AfpB+oH"},"xaxis":"x","y":{"dtype":"f8","bdata":"AAAAAAAAJED2KFyPwvUgQD0K16NwPRBA7FG4HoXrGUCkcD0K16MZQGZmZmZmZhpAmpmZmZkZIUC4HoXrUbgkQB+F61G4nilAcT0K16NwL0DXo3A9ClczQI\u002fC9ShcjzNA"},"yaxis":"y","type":"scatter"},{"fillpattern":{"shape":""},"hovertemplate":"\u003cb\u003e%{y:.2f} %\u003c\u002fb\u003e","legendgroup":"Nuclear","line":{"color":"#2E2252"},"marker":{"symbol":"circle"},"mode":"lines","name":"Nuclear","orientation":"v","showlegend":true,"stackgroup":"1","x":{"dtype":"i2","bdata":"3wfgB+EH4gfjB+QH5QfmB+cH6AfpB+oH"},"xaxis":"x","y":{"dtype":"f8","bdata":"hetRuB4FTkC4HoXrUXhOQMP1KFyPYk9ACtejcD2KTkCamZmZmXlOQM3MzMzMzE1AXI\u002fC9SgcTUBSuB6F69FKQHsUrkfhmkpAexSuR+F6SUA9CtejcB1IQIXrUbgeBUdA"},"yaxis":"y","type":"scatter"},{"fillpattern":{"shape":""},"hovertemplate":"\u003cb\u003e%{y:.2f} %\u003c\u002fb\u003e","legendgroup":"Hydro","line":{"color":"#554B8D"},"marker":{"symbol":"circle"},"mode":"lines","name":"Hydro","orientation":"v","showlegend":true,"stackgroup":"1","x":{"dtype":"i2","bdata":"3wfgB+EH4gfjB+QH5QfmB+cH6AfpB+oH"},"xaxis":"x","y":{"dtype":"f8","bdata":"KVyPwvWoN0A9CtejcL03QOF6FK5HITpASOF6FK6HOEBI4XoUroc4QI\u002fC9ShcDzlAAAAAAAAAOEBmZmZmZuY5QFK4HoXrETlAXI\u002fC9SgcOEDNzMzMzAw3QNejcD0KFzhA"},"yaxis":"y","type":"scatter"},{"fillpattern":{"shape":""},"hovertemplate":"\u003cb\u003e%{y:.2f} %\u003c\u002fb\u003e","legendgroup":"Wind","line":{"color":"#867CAE"},"marker":{"symbol":"circle"},"mode":"lines","name":"Wind","orientation":"v","showlegend":true,"stackgroup":"1","x":{"dtype":"i2","bdata":"3wfgB+EH4gfjB+QH5QfmB+cH6AfpB+oH"},"xaxis":"x","y":{"dtype":"f8","bdata":"ZmZmZmZmF0DNzMzMzMwYQHE9CtejcBlA4XoUrkfhHECamZmZmZkdQOxRuB6F6x9A16NwPQrXIEBI4XoUrsciQNejcD0KVyBACtejcD0KIUDsUbgehWshQFyPwvUoXCNA"},"yaxis":"y","type":"scatter"},{"fillpattern":{"shape":""},"hovertemplate":"\u003cb\u003e%{y:.2f} %\u003c\u002fb\u003e","legendgroup":"Biofuel","line":{"color":"#BCB8CD"},"marker":{"symbol":"circle"},"mode":"lines","name":"Biofuel","orientation":"v","showlegend":true,"stackgroup":"1","x":{"dtype":"i2","bdata":"3wfgB+EH4gfjB+QH5QfmB+cH6AfpB+oH"},"xaxis":"x","y":{"dtype":"f8","bdata":"j8L1KFyP0j8fhetRuB7VP9ejcD0K19M\u002fj8L1KFyP0j8AAAAAAADQPwAAAAAAANA\u002f7FG4HoXr0T\u002fhehSuR+HKP7gehetRuM4\u002fKVyPwvUozD8pXI\u002fC9SjMP6RwPQrXo9A\u002f"},"yaxis":"y","type":"scatter"},{"fillpattern":{"shape":""},"hovertemplate":"\u003cb\u003e%{y:.2f} %\u003c\u002fb\u003e","legendgroup":"Solar","line":{"color":"#D8D5DF"},"marker":{"symbol":"circle"},"mode":"lines","name":"Solar","orientation":"v","showlegend":true,"stackgroup":"1","x":{"dtype":"i2","bdata":"3wfgB+EH4gfjB+QH5QfmB+cH6AfpB+oH"},"xaxis":"x","y":{"dtype":"f8","bdata":"w\u002fUoXI\u002fCxT\u002fXo3A9CtfTP1K4HoXrUdg\u002f9ihcj8L12D9xPQrXo3DdP1K4HoXrUeA\u002f9ihcj8L14D9SuB6F61HgP1yPwvUoXN8\u002fuB6F61G43j\u002fNzMzMzMzcP1K4HoXrUdg\u002f"},"yaxis":"y","type":"scatter"}],                        {"template":{"data":{"barpolar":[{"marker":{"line":{"color":"white","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"white","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"#C8D4E3","linecolor":"#C8D4E3","minorgridcolor":"#C8D4E3","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"#C8D4E3","linecolor":"#C8D4E3","minorgridcolor":"#C8D4E3","startlinecolor":"#2a3f5f"},"type":"carpet"}],"choropleth":[{"colorbar":{"outlinewidth":0,"ticks":""},"type":"choropleth"}],"contourcarpet":[{"colorbar":{"outlinewidth":0,"ticks":""},"type":"contourcarpet"}],"contour":[{"colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"type":"contour"}],"heatmap":[{"colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"type":"heatmap"}],"histogram2dcontour":[{"colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"type":"histogram2dcontour"}],"histogram2d":[{"colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"type":"histogram2d"}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"mesh3d":[{"colorbar":{"outlinewidth":0,"ticks":""},"type":"mesh3d"}],"parcoords":[{"line":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"parcoords"}],"pie":[{"automargin":true,"type":"pie"}],"scatter3d":[{"line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scatter3d"}],"scattercarpet":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scattercarpet"}],"scattergeo":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scattergeo"}],"scattergl":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scattergl"}],"scattermapbox":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scattermapbox"}],"scattermap":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scattermap"}],"scatterpolargl":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scatterpolargl"}],"scatterpolar":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scatterpolar"}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"scatterternary":[{"marker":{"colorbar":{"outlinewidth":0,"ticks":""}},"type":"scatterternary"}],"surface":[{"colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"type":"surface"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}]},"layout":{"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"autotypenumbers":"strict","coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]],"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]},"colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"geo":{"bgcolor":"white","lakecolor":"white","landcolor":"white","showlakes":true,"showland":true,"subunitcolor":"#C8D4E3"},"hoverlabel":{"align":"left"},"hovermode":"closest","mapbox":{"style":"light"},"paper_bgcolor":"white","plot_bgcolor":"white","polar":{"angularaxis":{"gridcolor":"#EBF0F8","linecolor":"#EBF0F8","ticks":""},"bgcolor":"white","radialaxis":{"gridcolor":"#EBF0F8","linecolor":"#EBF0F8","ticks":""}},"scene":{"xaxis":{"backgroundcolor":"white","gridcolor":"#DFE8F3","gridwidth":2,"linecolor":"#EBF0F8","showbackground":true,"ticks":"","zerolinecolor":"#EBF0F8"},"yaxis":{"backgroundcolor":"white","gridcolor":"#DFE8F3","gridwidth":2,"linecolor":"#EBF0F8","showbackground":true,"ticks":"","zerolinecolor":"#EBF0F8"},"zaxis":{"backgroundcolor":"white","gridcolor":"#DFE8F3","gridwidth":2,"linecolor":"#EBF0F8","showbackground":true,"ticks":"","zerolinecolor":"#EBF0F8"}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"ternary":{"aaxis":{"gridcolor":"#DFE8F3","linecolor":"#A2B1C6","ticks":""},"baxis":{"gridcolor":"#DFE8F3","linecolor":"#A2B1C6","ticks":""},"bgcolor":"white","caxis":{"gridcolor":"#DFE8F3","linecolor":"#A2B1C6","ticks":""}},"title":{"x":0.05},"xaxis":{"automargin":true,"gridcolor":"#EBF0F8","linecolor":"#EBF0F8","ticks":"","title":{"standoff":15},"zerolinecolor":"#EBF0F8","zerolinewidth":2},"yaxis":{"automargin":true,"gridcolor":"#EBF0F8","linecolor":"#EBF0F8","ticks":"","title":{"standoff":15},"zerolinecolor":"#EBF0F8","zerolinewidth":2}}},"xaxis":{"anchor":"y","domain":[0.0,1.0],"title":{"text":"Year"}},"yaxis":{"anchor":"x","domain":[0.0,1.0],"title":{"text":"Percentage of Total Generation (%)"},"range":[0,100],"ticksuffix":"%"},"legend":{"title":{"text":"Generation Source"},"tracegroupgap":0},"title":{"text":"Ontario Electricity Generation Mix Shift"},"height":600,"width":1200,"hovermode":"x unified"},                        {"responsive": true}                    );                    Plotly.relayout("eab3d5a8-0d5c-4373-bf73-56277471f626", {autosize: true});                };            </script>        </div>"""
        ),
        "code_lines": "Calculating each fuel type's annual share of generation (T-SQL)",
        "code": (
            "WITH yearly_data AS (\n"
            "    SELECT\n"
            "        YEAR(month) AS year,\n"
            "        fuel,\n"
            "        SUM(output_gwh) AS fuel_output,\n"
            "        -- window-of-aggregate: inner SUM gives per-fuel annual totals,\n"
            "        -- outer SUM window adds them back up across all fuels in the\n"
            "        -- same year, giving the yearly total without a subquery\n"
            "        SUM(SUM(output_gwh)) OVER(PARTITION BY YEAR(month)) AS yearly_output\n"
            "    FROM generation\n"
            "    GROUP BY YEAR(month), fuel\n"
            ")\n"
            "SELECT\n"
            "    year,\n"
            "    fuel,\n"
            "    ROUND(fuel_output * 100.0 / yearly_output, 2) AS pct_of_total_generation\n"
            "FROM yearly_data\n"
            "ORDER BY year, fuel"
        ),
        "stack": ["Python", "Pandas", "Plotly", "Seaborn", "SQL Server 2022", "T-SQL", "Docker Compose"],
    },

    # --- Filler projects (placeholder content) --------------------------
    {
        "slug": "energy-audit-dashboard",
        "tagline": "Visualising residential audit data across Ontario",
        "why": (
            "After years of producing PDF audit reports, I wanted to aggregate findings "
            "across all my assessments and surface patterns that no single report could show "
            "— which upgrade paths offered the best return across different building "
            "vintages, how air leakage varied by construction era, and where fuel-switching "
            "made economic sense."
        ),
        "how": (
            "Exported 200+ EnerGuide audit records to CSV, cleaned and normalised fields "
            "with Pandas (handling inconsistent unit conventions and missing blower door "
            "values), then built a Streamlit dashboard with Plotly charts. The dashboard "
            "filters by municipality, building vintage decade, primary heating fuel, and "
            "upgrade path."
        ),
        "results": results_block([
            "Homes built before 1980 had median air leakage 2.4× higher than post-2000 stock",
            "Attic insulation upgrades showed the highest average energy savings per dollar across all vintages",
            "Natural gas to heat pump conversions were cost-effective in only 38% of assessed homes under current tariffs",
            "Dashboard reduced time-to-insight for upgrade prioritisation from hours to minutes",
        ]),
        "code_lines": "Normalising air leakage across measurement vintages",
        "code": (
            "# ACH50 values pre-2015 used a different reference pressure\n"
            "def normalise_ach50(row):\n"
            "    if row['audit_year'] < 2015 and row['test_pressure'] == 75:\n"
            "        return row['ach50'] * 0.92  # empirical correction factor\n"
            "    return row['ach50']\n"
            "\n"
            "df['ach50_norm'] = df.apply(normalise_ach50, axis=1)"
        ),
        "stack": ["Python 3.11", "Pandas 2.0", "Plotly 5.x", "Streamlit", "NumPy", "OpenPyXL"],
    },
    {
        "slug": "hvac-efficiency-classifier",
        "tagline": "ML model for HVAC efficiency tier classification",
        "why": (
            "During audits, homeowners often could not locate their equipment manuals, "
            "making it hard to record accurate efficiency ratings. I wanted a model that "
            "could infer efficiency tier from observable characteristics — serial number "
            "patterns, physical dimensions, refrigerant type, and installation year — "
            "without needing the original spec sheet."
        ),
        "how": (
            "Collected a labelled dataset of 1,200 HVAC units from manufacturer databases "
            "and field observations. Features included installation decade, refrigerant type "
            "(R-22 vs R-410A), compressor stage count, and visible coil configuration. "
            "Trained a Random Forest classifier with cross-validation, then evaluated on a "
            "held-out test split."
        ),
        "results": results_block([
            "91% accuracy on the held-out test set across three efficiency tiers",
            "Refrigerant type and installation decade were the two highest-importance features",
            "Reduced field data collection time per unit by approximately 8 minutes",
            "False-negative rate on low-efficiency tier was 4.2%, acceptable for advisory use",
        ]),
        "code_lines": "Feature importance extraction and visualisation",
        "code": (
            "importances = pd.Series(\n"
            "    clf.feature_importances_,\n"
            "    index=feature_names\n"
            ").sort_values(ascending=False)\n"
            "\n"
            "ax.barh(importances.index[:10], importances.values[:10],\n"
            "        color='#d97b3a', edgecolor='none')"
        ),
        "stack": ["Python 3.11", "scikit-learn", "Pandas", "Matplotlib", "Joblib"],
    },
    {
        "slug": "enerquery",
        "tagline": "CLI for querying NRCan EnerGuide open datasets",
        "why": (
            "The NRCan EnerGuide open dataset is invaluable for energy research but "
            "notoriously inconsistent — column names changed across annual releases, units "
            "mix imperial and metric, and some provinces encode values differently. I built "
            "enerquery so any analyst could load, filter, and export clean data in one "
            "command rather than wrestling with the raw CSVs."
        ),
        "how": (
            "Built as a Python CLI using Click. A schema-mapping layer normalises column "
            "names across all dataset vintages (2011–2024). Unit conversion functions handle "
            "BTU/hr ↔ kW, ft² ↔ m², and ACH conversions. Provincial filters and vintage-year "
            "flags are exposed as CLI options. Output can be CSV, JSON, or a Pandas-ready "
            "Parquet file."
        ),
        "results": results_block([
            "Supports all NRCan EnerGuide releases from 2011 to 2024",
            "Reduces data prep time from 2–4 hours to under 5 minutes for a typical analysis",
            "Zero external dependencies beyond Click, Pandas, and PyArrow",
        ]),
        "code_lines": "Schema normalisation across dataset vintages",
        "code": (
            "COLUMN_MAP = {\n"
            "    # 2011-2016 names -> canonical\n"
            "    'HVAC_HEAT_TYPE': 'heating_system_type',\n"
            "    'BLOWER_DOOR_ACH': 'ach50',\n"
            "    # 2017+ names -> canonical\n"
            "    'heating_type_desc': 'heating_system_type',\n"
            "    'air_leakage_ach50': 'ach50',\n"
            "}\n"
            "\n"
            "def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    return df.rename(columns=COLUMN_MAP)"
        ),
        "stack": ["Python 3.11", "Click", "Pandas", "PyArrow", "pytest"],
    },
    {
        "slug": "sql-energy-queries",
        "tagline": "Annotated SQL for energy billing databases",
        "why": (
            "Most energy billing analysis tutorials assume clean, well-structured data. "
            "Real utility billing databases have gaps, rate-class changes mid-year, and "
            "consumption recorded in inconsistent intervals. This repository documents the "
            "SQL patterns I developed to handle those realities."
        ),
        "how": (
            "Queries are organised by use case: interval aggregation, weather "
            "normalisation using heating degree days, rate-class pivot tables, and "
            "year-over-year variance analysis. Each query includes inline comments "
            "explaining the domain rationale, not just the SQL logic. Tested against a "
            "synthetic billing database modelled on Ontario utility data."
        ),
        "results": results_block([
            "32 annotated queries across 6 analytical categories",
            "Weather-normalisation query reduces HDD-correlated variance by ~60% in test dataset",
            "Included CTEs reduce average query length by 40% vs equivalent subquery versions",
        ]),
        "code_lines": "Weather-normalised annual consumption baseline",
        "code": (
            "WITH hdd AS (\n"
            "  SELECT year, SUM(heating_degree_days) AS annual_hdd\n"
            "  FROM weather_station\n"
            "  GROUP BY year\n"
            "),\n"
            "baseline_hdd AS (\n"
            "  SELECT AVG(annual_hdd) AS hdd_30yr FROM hdd\n"
            "  WHERE year BETWEEN 1990 AND 2020\n"
            ")\n"
            "SELECT\n"
            "  b.account_id,\n"
            "  b.year,\n"
            "  b.consumption_kwh * (bh.hdd_30yr / h.annual_hdd) AS normalised_kwh\n"
            "FROM billing b\n"
            "JOIN hdd h USING (year)\n"
            "CROSS JOIN baseline_hdd bh"
        ),
        "stack": ["PostgreSQL 15", "SQLite (for portability)", "Python (test harness)", "DBeaver"],
    },
]


BLOG_SEED = [
    {
        "slug": "pandas-groupby-energy-reports",
        "title": "Why Pandas groupby Clicked Once I Thought About Energy Reports",
        "date_display": "Jun 18, 2026",
        "read_time": "6 min",
        "excerpt": (
            "I spent years aggregating energy data in Excel pivot tables. Learning groupby felt "
            "instantly familiar — here is how domain knowledge accelerated my mental model."
        ),
        "tags": ["pandas", "python", "learning"],
        "body": (
            "## The Excel pivot table era\n"
            "\n"
            "For three years, every audit I filed ended with the same ritual: export a CSV "
            "from the EnerGuide software, open Excel, build a pivot table, and spend twenty "
            "minutes coaxing it into the summary my supervisor wanted. I could do it fast. I "
            "knew every shortcut. But I never thought of it as programming — it was just how "
            "reports got made.\n"
            "\n"
            "When I started learning Python, I kept hitting a wall with groupby. The "
            "documentation made sense in isolation, but I could not hold the mental model "
            "together when I tried to use it on real data.\n"
            "\n"
            "## The moment it clicked\n"
            "\n"
            "The breakthrough came when I stopped thinking about groupby as a Python concept "
            "and started thinking about it as a pivot table I already knew. A pivot table has "
            "three things: the column you group by (the row field), the values you aggregate "
            "(the value field), and the function you apply (sum, average, count). groupby has "
            "exactly the same structure.\n"
            "\n"
            "Grouping audit records by building vintage decade — the pivot table I used to "
            "build manually in Excel, translated directly:\n"
            "\n"
            "```python\n"
            "# Row field: vintage_decade\n"
            "# Value field: ach50\n"
            "# Function: mean\n"
            "\n"
            "df['vintage_decade'] = (df['build_year'] // 10) * 10\n"
            "\n"
            "summary = (\n"
            "    df\n"
            "    .groupby('vintage_decade')['ach50']\n"
            "    .agg(['mean', 'median', 'count'])\n"
            "    .round(2)\n"
            ")\n"
            "print(summary)\n"
            "```\n"
            "\n"
            "## Domain knowledge as a learning accelerant\n"
            "\n"
            "The broader lesson is that existing domain knowledge is not neutral when you are "
            "learning data tools — it actively accelerates comprehension. Every time I hit a "
            "new concept, I ask: what is the energy equivalent of this? Merge is a vlookup. A "
            "DataFrame is an audit spreadsheet with named columns. A distribution is the spread "
            "of air leakage readings across a hundred homes.\n"
            "\n"
            "If you are transitioning into data from a technical field, lean into the "
            "analogies. Your mental models are not just comforting — they are genuinely "
            "useful scaffolding.\n"
            "\n"
            "## What I would tell past me\n"
            "\n"
            "Stop trying to learn Python in the abstract. Find the data you already understand "
            "and apply the tools to it immediately. The first time groupby returned a summary "
            "that matched my Excel pivot exactly, I understood it properly for the first time. "
            "Not because I had read more documentation, but because I had a ground truth to "
            "compare against.\n"
            "\n"
            "Learning tools on familiar data removes one variable from an already complex "
            "equation. You only have to learn the syntax, not the domain and the syntax "
            "simultaneously.\n"
        ),
    },
    {
        "slug": "cleaning-energy-audit-exports",
        "title": "Energy Data is Messy: A Field Guide to Cleaning Audit Exports",
        "date_display": "May 30, 2026",
        "read_time": "9 min",
        "excerpt": (
            "NRCan exports are inconsistent across provinces and vintages. This post documents "
            "every edge case I encountered and the Pandas pipeline I built to handle them."
        ),
        "tags": ["data-cleaning", "energy", "python"],
        "body": (
            "## The illusion of clean government data\n"
            "\n"
            "When I started pulling NRCan EnerGuide open datasets into Pandas, I expected clean, "
            "well-documented CSVs. The federal government publishes this data publicly, it has "
            "been collected for decades, and the EnerGuide methodology is tightly standardised. "
            "Surely the exports would be consistent.\n"
            "\n"
            "They were not. After loading data from three provincial exports, I had 47 unique "
            "column names representing the same 12 underlying fields, unit inconsistencies that "
            "mixed BTU/hr with kW in the same file, and air leakage values that were clearly "
            "recorded at different reference pressures without labelling.\n"
            "\n"
            "## The five categories of mess\n"
            "\n"
            "After working through several vintages I grouped the problems into five categories: "
            "column name drift (the same field renamed across annual releases), unit mixing "
            "(imperial and metric values in the same column), encoding artifacts (French accented "
            "characters corrupting province names), missing value sentinels (using 0 to mean "
            "missing rather than NaN), and duplicate records (the same audit appearing twice "
            "after provincial merges).\n"
            "\n"
            "Detecting and replacing numeric missing-value sentinels:\n"
            "\n"
            "```python\n"
            "# ACH50 of exactly 0.0 indicates a missing test, not a perfect building\n"
            "SENTINEL_COLS = ['ach50', 'heat_loss_coefficient', 'window_area_m2']\n"
            "\n"
            "for col in SENTINEL_COLS:\n"
            "    n_zeros = (df[col] == 0).sum()\n"
            "    if n_zeros > 0:\n"
            "        print(f\"{col}: replacing {n_zeros} zero sentinels with NaN\")\n"
            "    df[col] = df[col].replace(0, float('nan'))\n"
            "```\n"
            "\n"
            "## Building a repeatable cleaning pipeline\n"
            "\n"
            "The key design decision was to make every cleaning step explicit, logged, and "
            "reversible. Rather than mutating the raw DataFrame in place, I built a pipeline of "
            "functions that each take a DataFrame and return a cleaned copy with a log entry. "
            "This means I can audit exactly what changed and replay the pipeline on new data "
            "exports without re-investigating the same edge cases.\n"
            "\n"
            "## What the mess teaches you\n"
            "\n"
            "Messy data is not a problem to eliminate — it is information. The inconsistencies "
            "in the NRCan exports reflect the reality of a program administered across thirteen "
            "jurisdictions over thirty years, with different software systems, different field "
            "workers, and evolving methodology. Understanding why the data is messy makes you a "
            "better analyst, not just a cleaner of other people's mistakes.\n"
        ),
    },
    {
        "slug": "blower-door-to-box-plots",
        "title": "From Blower Door Tests to Box Plots: Reading Distributions as an Energy Advisor",
        "date_display": "Apr 22, 2026",
        "read_time": "5 min",
        "excerpt": (
            "Statistical distributions made intuitive sense the moment I mapped them onto air "
            "leakage variance across building types I had personally tested."
        ),
        "tags": ["statistics", "visualisation", "energy"],
        "body": (
            "## What a blower door test actually measures\n"
            "\n"
            "A blower door test pressurises a house to 50 Pascals and measures how much air "
            "flows through the building envelope to maintain that pressure. The result — ACH50, "
            "air changes per hour at 50 Pa — is a single number that summarises the combined "
            "leakiness of every crack, gap, and penetration in the building.\n"
            "\n"
            "Over three years I ran this test on hundreds of homes. What struck me was the "
            "variance. Two 1970s bungalows of identical floor area, same construction type, "
            "same climate zone, could have ACH50 values that differed by a factor of three.\n"
            "\n"
            "## Box plots as a field intuition, formalised\n"
            "\n"
            "When I first saw a box plot in a statistics tutorial I already understood it "
            "intuitively, I just did not know the vocabulary. The median was the typical house "
            "I expected to walk into. The interquartile range was the normal spread of outcomes "
            "— not surprising, but variable. The whiskers were the houses that made me stop and "
            "wonder what had happened during construction. The outliers were the ones I wrote up "
            "as case studies.\n"
            "\n"
            "Air leakage distribution by building vintage:\n"
            "\n"
            "```python\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "fig, ax = plt.subplots(figsize=(10, 5))\n"
            "\n"
            "vintages = df.groupby('vintage_decade')['ach50'].apply(list)\n"
            "ax.boxplot(\n"
            "    [v for v in vintages],\n"
            "    labels=[str(d) + 's' for d in vintages.index],\n"
            "    patch_artist=True,\n"
            "    boxprops=dict(facecolor='#d97b3a', alpha=0.4),\n"
            "    medianprops=dict(color='#d97b3a', linewidth=2),\n"
            ")\n"
            "ax.set_ylabel('ACH50')\n"
            "ax.set_title('Air leakage by construction decade')\n"
            "```\n"
            "\n"
            "## The translation that makes statistics land\n"
            "\n"
            "The broader point is that statistical concepts land fastest when you have a "
            "physical intuition to attach them to. Variance was not an abstract formula once I "
            "thought of it as the range of houses I had actually tested. A skewed distribution "
            "was not a mathematical curiosity once I connected it to the fact that there is a "
            "floor on how airtight a house can be but no practical ceiling on how leaky.\n"
            "\n"
            "If you are coming from a technical field into data analysis, find your blower door "
            "equivalent. The concept you have already built physical intuition for is the one "
            "that will make the statistics feel obvious.\n"
        ),
    },
    {
        "slug": "first-sql-database-audit-records",
        "title": "Building My First SQL Database for Audit Records",
        "date_display": "Mar 14, 2026",
        "read_time": "8 min",
        "excerpt": (
            "I took six months of paper audit forms and designed a relational schema around "
            "them. Here is what domain expertise taught me about table design that tutorials "
            "never mention."
        ),
        "tags": ["sql", "database-design", "energy"],
        "body": (
            "## The paper form as a data model\n"
            "\n"
            "Before I learned SQL, I spent six months filling out the same paper audit form for "
            "every assessment. The form had sections: property information, envelope "
            "measurements, mechanical systems, air leakage results, and recommended upgrades. "
            "Each section had fields. Some fields repeated — a house might have three heating "
            "zones, each with its own equipment.\n"
            "\n"
            "When I finally sat down to design my first relational database, I realised I had "
            "been thinking in tables for years. The form sections were my tables. The repeating "
            "fields were my one-to-many relationships.\n"
            "\n"
            "## Where tutorials mislead you\n"
            "\n"
            "Most SQL tutorials teach you to design tables around nouns: users, products, "
            "orders. The implicit assumption is that each noun maps cleanly to one table. "
            "Real-world data is messier. An energy audit has a property, but a property can "
            "have multiple audits over time. An audit has multiple mechanical systems. A "
            "mechanical system has multiple components, each with its own efficiency rating.\n"
            "\n"
            "Domain knowledge told me immediately that a flat `audits` table was wrong — I had "
            "filled out too many forms where the same property appeared twice because the "
            "homeowner had done upgrades and wanted a follow-up assessment.\n"
            "\n"
            "Core schema: properties and audits as separate entities:\n"
            "\n"
            "```sql\n"
            "CREATE TABLE properties (\n"
            "  id         SERIAL PRIMARY KEY,\n"
            "  address    TEXT NOT NULL,\n"
            "  city       TEXT,\n"
            "  province   CHAR(2),\n"
            "  build_year INT\n"
            ");\n"
            "\n"
            "CREATE TABLE audits (\n"
            "  id            SERIAL PRIMARY KEY,\n"
            "  property_id   INT REFERENCES properties(id),\n"
            "  audit_date    DATE NOT NULL,\n"
            "  advisor_id    INT,\n"
            "  ach50         NUMERIC(5,2),\n"
            "  heating_fuel  TEXT\n"
            ");\n"
            "```\n"
            "\n"
            "## The upgrade path problem\n"
            "\n"
            "The trickiest design decision was modelling recommended upgrade paths. An audit "
            "produces a ranked list of upgrades — attic insulation, air sealing, heating system "
            "replacement — each with an estimated cost and estimated annual savings. But "
            "upgrades interact: sometimes doing attic insulation first changes the savings "
            "estimate for air sealing.\n"
            "\n"
            "I ended up with a separate `upgrade_recommendations` table with a `depends_on` "
            "self-referential foreign key. That pattern took me three rewrites to land on, and "
            "I only got there because I had sat with homeowners while explaining exactly these "
            "trade-offs.\n"
            "\n"
            "## What I would do differently\n"
            "\n"
            "Start with the queries you know you need to run, not the tables you think you need "
            "to create. I knew from day one that I wanted to answer: which upgrade paths were "
            "most commonly recommended for pre-1980 homes heated by natural gas? Designing "
            "backwards from that question would have saved me two table rewrites. The schema "
            "should serve the questions, not the other way around.\n"
        ),
    },
]


def seed():
    with app.app_context():
        for entry in PROJECTS_SEED:
            existing = db.session.get(Project, entry["slug"])
            if existing:
                for key, value in entry.items():
                    setattr(existing, key, value)
                print(f"Updated project: {entry['slug']}")
            else:
                db.session.add(Project(**entry))
                print(f"Inserted project: {entry['slug']}")

        for entry in BLOG_SEED:
            existing = db.session.get(BlogPost, entry["slug"])
            if existing:
                for key, value in entry.items():
                    setattr(existing, key, value)
                print(f"Updated post: {entry['slug']}")
            else:
                db.session.add(BlogPost(**entry))
                print(f"Inserted post: {entry['slug']}")

        db.session.commit()
        print(f"Done — {len(PROJECTS_SEED)} project(s), {len(BLOG_SEED)} post(s) seeded.")


if __name__ == "__main__":
    seed()
