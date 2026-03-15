import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State
import numpy as np
import shapefile  # PyShp
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import copy
import os



# Path to the shapefile (already extracted)
shp_path = "counties/cb_2023_us_county_20m.shp"

# Read using PyShp
sf = shapefile.Reader(shp_path)

# Convert to GeoDataFrame manually
records = sf.records()
fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag
df = pd.DataFrame(records, columns=fields)

# Convert geometry
geoms = [shape(s) for s in sf.shapes()]
gdf = gpd.GeoDataFrame(df, geometry=geoms)

# Make GEOID a string
gdf["GEOID"] = gdf["GEOID"].astype(str)

df = pd.read_csv("1968_elections.csv")

df["fips"] = df["fips"].astype(str).str.zfill(5)

df["state_fips"] = df["fips"].str[:2]

state_df = (
    df.groupby("state_fips")
      .agg({
          "nixon_votes": "sum",
          "humphrey_votes": "sum",
          "wallace_votes": "sum"
      })
      .reset_index()
)

state_df["state_fips"] = state_df["state_fips"].astype(str).str.zfill(2)

fips_to_state = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT',
    '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI', '16': 'ID', '17': 'IL',
    '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD',
    '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE',
    '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND',
    '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD',
    '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV',
    '55': 'WI', '56': 'WY'
}



def get_rank(row):

    votes = {
        "R": row["nixon_votes"],
        "D": row["humphrey_votes"],
        "I": row["wallace_votes"]
    }

    ordered = sorted(votes, key=votes.get, reverse=True)
    return ordered[0] + ordered[1]

state_df["Rank"] = state_df.apply(get_rank, axis=1)

state_df['state_abbrev'] = state_df['state_fips'].map(fips_to_state)



# --- color map ---
color_map = {
    "RD": "#E81B23",
    "DR": "#4575b4",
    "RI": "#E81B23",
    "IR": "#00ff00",
    "DI": "#4575b4",
    "ID": "#00ff00"
}



state_map_fig = px.choropleth(
    state_df,
    locations="state_abbrev",
    locationmode="USA-states",
    color="Rank",
    scope="usa",
    color_discrete_map=color_map
)

state_map_fig.update_layout(showlegend=False)
#,
 #   paper_bgcolor="#f9f7f4",
  #  plot_bgcolor="#f9f7f4",
   # font=dict(family="Playfair Display, serif", color="#1a1a1a"))


for trace in state_map_fig.data:
    trace.legendgroup = trace.name
    
    
    
# Build state-level centroids for dot overlays
state_centroids = gdf.copy()
state_centroids["state_fips"] = state_centroids["GEOID"].str[:2]
state_centroids = state_centroids.dissolve(by="state_fips").reset_index()
state_centroids["lon"] = state_centroids["geometry"].apply(
    lambda g: g.centroid.x if g is not None else None)
state_centroids["lat"] = state_centroids["geometry"].apply(
    lambda g: g.centroid.y if g is not None else None)

# Merge rank onto state centroids
state_centroids = state_centroids.merge(
    state_df[["state_fips", "Rank"]], on="state_fips", how="left")

ri_s = state_centroids[state_centroids["Rank"] == "RI"]
di_s = state_centroids[state_centroids["Rank"] == "DI"]
ir_s = state_centroids[state_centroids["Rank"] == "IR"]

state_map_fig.add_scattergeo(
    lon=ri_s["lon"], lat=ri_s["lat"], mode="markers",
    marker=dict(size=8, color="#00ff00", opacity=0.8),
    legendgroup="RI", showlegend=False, hoverinfo="skip"
)
state_map_fig.add_scattergeo(
    lon=di_s["lon"], lat=di_s["lat"], mode="markers",
    marker=dict(size=8, color="#00ff00", opacity=0.8),
    legendgroup="DI", showlegend=False, hoverinfo="skip"
)
state_map_fig.add_scattergeo(
    lon=ir_s["lon"], lat=ir_s["lat"], mode="markers",
    marker=dict(size=8, color="red", opacity=0.8),
    legendgroup="IR", showlegend=False, hoverinfo="skip"
)

#state_map_fig.update_layout(showlegend=False)
#, 
 #                          font=dict(family="Playfair Display, serif", color="#1a1a1a"), 
  #                         paper_bgcolor="#f9f7f4",
   #                         plot_bgcolor="#f9f7f4")
    
    
gdf2 = df.merge(gdf, right_on="GEOID", left_on="fips", how="left")





# --- Build choropleth ---
map_fig = px.choropleth(
    df,
    geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
    locations="fips",
    color="Rank",
    scope="usa",
    color_discrete_map=color_map,
    hover_name="county",
)

map_fig.update_layout(showlegend=False)

# 🔹 Link choropleth traces to legend groups
for trace in map_fig.data:
    trace.legendgroup = trace.name


# --- centroid coordinates ---
gdf2["lon"] = gdf2["geometry"].apply(lambda geom: geom.centroid.x if geom is not None else None)
gdf2["lat"] = gdf2["geometry"].apply(lambda geom: geom.centroid.y if geom is not None else None)

ri_df = gdf2[gdf2["Rank"] == "RI"]
di_df = gdf2[gdf2["Rank"] == "DI"]
ir_df = gdf2[gdf2["Rank"] == "IR"]


# --- overlay dots (hidden from legend) ---
map_fig.add_scattergeo(
    lon=ri_df["lon"],
    lat=ri_df["lat"],
    mode="markers",
    marker=dict(size=7, color="#00ff00", opacity=0.8),
    legendgroup="RI",
    showlegend=False,
    hoverinfo="skip"
)

map_fig.add_scattergeo(
    lon=di_df["lon"],
    lat=di_df["lat"],
    mode="markers",
    marker=dict(size=7, color="#00ff00", opacity=0.8),
    legendgroup="DI",
    showlegend=False,
    hoverinfo="skip"
)

map_fig.add_scattergeo(
    lon=ir_df["lon"],
    lat=ir_df["lat"],
    mode="markers",
    marker=dict(size=7, color="red", opacity=0.8),
    legendgroup="IR",
    showlegend=False,
    hoverinfo="skip"
)

map_fig.update_layout(uirevision="keep")



ri_legend = html.Div("RI legend placeholder")
di_legend = html.Div("DI legend placeholder")
ir_legend = html.Div("IR legend placeholder")

# --- proxy legend traces ---
# these control the legend appearance + toggling

def add_proxy(rank, square_color, dot_color=None):
    # square
    map_fig.add_scattergeo(
        lon=[None],
        lat=[None],
        mode="markers",
        marker=dict(size=12, color=square_color, symbol="square"),
        legendgroup=rank,
        name=rank,
        showlegend=False
    )

    # optional dot overlay (hidden)
    if dot_color:
        map_fig.add_scattergeo(
            lon=[None],
            lat=[None],
            mode="markers",
            marker=dict(size=6, color=dot_color),
            legendgroup=rank,
            showlegend=False
        )


add_proxy("RI", "#E81B23", "#00ff00")
add_proxy("DI", "#4575b4", "#00ff00")
add_proxy("IR", "#00ff00", "red")


# --- legend behavior ---
map_fig.update_layout(
    legend=dict(groupclick="togglegroup"))

map_fig.update_geos(fitbounds="locations", visible=False)

map_fig.update_layout(showlegend=False)



app = dash.Dash(__name__)
server = app.server

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>1968 Election</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;900&display=swap" rel="stylesheet">
        <style>
            * { font-family: 'Playfair Display', serif; }
            body { background-color: #f9f7f4; margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        {%app_entry%}
        {%config%}
        {%scripts%}
        {%renderer%}
    </body>
</html>
'''



def add_dot_overlays(fig, source_df):
    """Add green dots on RI/DI counties and red dots on IR counties."""
    
    # We need centroids — merge with gdf to get them
    merged = source_df.merge(gdf[["GEOID", "geometry"]], 
                              left_on="fips", right_on="GEOID", how="left")
    merged["lon"] = merged["geometry"].apply(
        lambda g: g.centroid.x if g is not None else None)
    merged["lat"] = merged["geometry"].apply(
        lambda g: g.centroid.y if g is not None else None)

    ri_df = merged[merged["Rank"] == "RI"]
    di_df = merged[merged["Rank"] == "DI"]
    ir_df = merged[merged["Rank"] == "IR"]

    fig.add_scattergeo(
        lon=ri_df["lon"], lat=ri_df["lat"],
        mode="markers",
        marker=dict(size=5, color="#00ff00", opacity=0.8),
        legendgroup="RI", showlegend=False, hoverinfo="skip"
    )
    fig.add_scattergeo(
        lon=di_df["lon"], lat=di_df["lat"],
        mode="markers",
        marker=dict(size=5, color="#00ff00", opacity=0.8),
        legendgroup="DI", showlegend=False, hoverinfo="skip"
    )
    fig.add_scattergeo(
        lon=ir_df["lon"], lat=ir_df["lat"],
        mode="markers",
        marker=dict(size=5, color="red", opacity=0.8),
        legendgroup="IR", showlegend=False, hoverinfo="skip"
    )
    return fig



county_counts = (
    df["Rank"]
    .value_counts()
    .reindex(["RD", "DR", "RI", "DI", "IR", "ID"], fill_value=0)
    .reset_index()
)

county_counts.columns = ["Rank", "Count"]
county_counts = county_counts.sort_values(by = "Count", ascending = False)


color_map_outline = {
    "RD": "#4575b4",
    "DR": "#E81B23",
    "RI": "#00ff00",
    "IR": "#E81B23",
    "DI": "#00ff00",
    "ID": "#4575b4"
}


summary_fig = px.bar(
    county_counts,
    x="Rank",
    y="Count",
    color="Rank",
    color_discrete_map=color_map,
    title="County Type Counts"
)

# Match outline color to fill color per trace
for trace in summary_fig.data:
    rank_name = trace.name  # this corresponds to the Rank category
    outline_color = color_map_outline.get(rank_name, "black")

    trace.marker.line.color = outline_color
    trace.marker.line.width = 4

summary_fig.update_layout(showlegend=False)



ri_legend = html.Div([

    # stacked square + dot
    html.Div([
        html.Div(style={
            "width": "16px",
            "height": "16px",
            "background": "#E81B23",   # square color
            "position": "relative"
        }),
        html.Div(style={
            "width": "6px",
            "height": "6px",
            "background": "#00ff00",   # dot color
            "borderRadius": "50%",
            "position": "absolute",
            "top": "5px",
            "left": "5px"
        })
    ], style={"position": "relative", "marginRight": "8px"}),

    html.Span("RI")

],
id="legend-ri",
style={
    "display": "flex",
    "alignItems": "center",
    "cursor": "pointer",
    "marginBottom": "6px"
})



di_legend = html.Div([

    html.Div([
        html.Div(style={
            "width": "16px",
            "height": "16px",
            "background": "#4575b4"
        }),
        html.Div(style={
            "width": "6px",
            "height": "6px",
            "background": "#00ff00",
            "borderRadius": "50%",
            "position": "absolute",
            "top": "5px",
            "left": "5px"
        })
    ], style={"position": "relative", "marginRight": "8px"}),

    html.Span("DI")

],
id="legend-di",
style={
    "display": "flex",
    "alignItems": "center",
    "cursor": "pointer",
    "marginBottom": "6px"
})


ir_legend = html.Div([

    html.Div([
        html.Div(style={
            "width": "16px",
            "height": "16px",
            "background": "#00ff00"
        }),
        html.Div(style={
            "width": "6px",
            "height": "6px",
            "background": "red",
            "borderRadius": "50%",
            "position": "absolute",
            "top": "5px",
            "left": "5px"
        })
    ], style={"position": "relative", "marginRight": "8px"}),

    html.Span("IR")

],
id="legend-ir",
style={
    "display": "flex",
    "alignItems": "center",
    "cursor": "pointer",
    "marginBottom": "6px"
})



def fetch_results(county_fips):
    county_fips = str(county_fips).zfill(5)
    df_slice = df[df["fips"] == county_fips]   # ← lowercase "fips"

    if df_slice.empty:
        return [], [], "Unknown County"

    row = df_slice.iloc[0]
    county_name = row["county"]                # ← lowercase "county"

    results = {
        "Richard Nixon":   row["nixon_votes"],
        "Hubert Humphrey": row["humphrey_votes"],
        "George Wallace":  row["wallace_votes"]
    }
    results = dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
    return list(results.keys()), np.array(list(results.values())), county_name




def make_legend_item(label, square_color, dot_color=None, legend_id=""):

    symbol = html.Div([
        html.Div(style={
            "width": "16px",
            "height": "16px",
            "background": square_color
        }),
    ], style={"position": "relative"})

    # optional dot overlay
    if dot_color:
        symbol.children.append(
            html.Div(style={
                "width": "6px",
                "height": "6px",
                "background": dot_color,
                "borderRadius": "50%",
                "position": "absolute",
                "top": "5px",
                "left": "5px"
            })
        )

    return html.Div(
        [symbol, html.Span(label)],
        id=legend_id,
        style={
            "display": "flex",
            "alignItems": "center",
            "cursor": "pointer",
            "marginBottom": "6px",
            "gap": "8px"
        }
    )


legend_items = [

    make_legend_item("RD", "#E81B23", legend_id="legend-rd"),
    make_legend_item("DR", "#4575b4", legend_id="legend-dr"),

    make_legend_item("RI", "#E81B23", "#00ff00", "legend-ri"),
    make_legend_item("DI", "#4575b4", "#00ff00", "legend-di"),
    make_legend_item("IR", "#00ff00", "red", "legend-ir"),

    make_legend_item("ID", "#00ff00", legend_id="legend-id"),
]


app.layout = html.Div([
    
    dcc.Store(id="map-level", data="state"),
    dcc.Store(id="current-state-fips", data=None),
    dcc.Store(id="current-state-name", data = None),
    
    # Replace the existing html.H1 with this:
html.Div([
    html.Div([
        html.H2(
            "1968 Presidential Election Results",
            style={
                "fontFamily": "Playfair Display, serif",
                "fontWeight": "900",
                "fontSize": "28px",
                "letterSpacing": "0.5px",
                "margin": "0",
                "color": "#1a1a1a"
            }
        ),
        html.H3(
            id="dashboard-title",
            children="Select a State",
            style={
                "fontFamily": "Playfair Display, serif",
                "fontWeight": "400",
                "fontStyle": "italic",
                "fontSize": "16px",
                "margin": "4px 0 0 0",
                "color": "#555"
            }
        )
    ], style={
        "borderBottom": "2px solid #1a1a1a",
        "paddingBottom": "12px",
        "paddingLeft": "50px",
        "paddingTop": "20px"
    })
], style={
    "width": "100%",
    "marginBottom": "20px",
    "backgroundColor": "#f9f7f4"
}),

    # ===== TOP ROW =====
    html.Div([
        

        # COLUMN 1 — MAP
        html.Div([
            html.Button(
                "← Back",
                id="back-btn",
                style={
                    "display": "none",          # hidden by default
                    "position": "absolute",
                    "top": "12px",
                    "left": "12px",
                    "zIndex": 999,
                    "padding": "6px 14px",
                    "background": "#1a1a2e",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "6px",
                    "cursor": "pointer",
                    "fontWeight": "bold",
                    "fontSize": "14px",
                    "boxShadow": "0 2px 6px rgba(0,0,0,0.4)"
                }
    ),
            dcc.Graph(id="county-map", figure=state_map_fig)
        ], style={
            "width": "60%",
            "border": "2px solid black", 
            "margin-left": "50px", 
            "position": "relative"
        }),

        # COLUMN 2 — LEGEND
        html.Div([
            html.H4("Legend"),
            *legend_items
        ], style={
            "width": "5%",
            "padding": "5px",
            "marginTop": "125px"
        }),

        # COLUMN 3 — INTERACTIVE BAR
        html.Div([
            dcc.Graph(id="county-bar")
        ], style={
            "width": "35%",
            "padding": "10px"
        }),

    ], style={
        "display": "flex",
        "alignItems": "flex-start"
    }),

    # ===== BOTTOM ROW =====
    html.Div([
        dcc.Graph(id="summary-bar", style = {"width":"50%"}),
        dcc.Graph(id = "simplex-chart", style={"width":"50%"})
    ], style={
        "display": "flex",
        "alignItems":"flex-start",
        "width": "100%",
        "marginTop": "20px"
    })

])



#I believe this will eventually be scrapped b/c this is the name of the dashboard, not the title of the chart. 
@app.callback(
    Output("dashboard-title", "children"),
    Input("map-level", "data"),
    Input("current-state-name", "data")
    #State("county-map", "clickData")
)
def update_title(level, state_name):
    if level == "county" and state_name:
        return state_name
    return "Select a State"



@app.callback(
    Output("simplex-chart", "figure"),
    Input("map-level", "data"),
    Input("current-state-fips", "data")
)
def update_simplex(level, state_fips):

    # Background layer — all counties, very faint
    bg = px.scatter_ternary(
        df,
        a="nixon_share",
        b="humphrey_share",
        c="wallace_share",
        color="Rank",
        color_discrete_map=color_map,
        hover_name="county",
        hover_data={
            "nixon_share": ":.1%",
            "humphrey_share": ":.1%",
            "wallace_share": ":.1%"
        }
    )

    # Set all background traces to very faint
    for trace in bg.data:
        trace.marker.opacity = 0.05
        trace.showlegend = False

    if level == "county" and state_fips is not None:
        state_counties = df[df["fips"].str[:2] == state_fips]

        fg = px.scatter_ternary(
            state_counties,
            a="nixon_share",
            b="humphrey_share",
            c="wallace_share",
            color="Rank",
            color_discrete_map=color_map,
            hover_name="county",
            hover_data={
                "nixon_share": ":.1%",
                "humphrey_share": ":.1%",
                "wallace_share": ":.1%"
            }
        )

        for trace in fg.data:
            trace.marker.opacity = 1.0
            trace.marker.size = 8
            trace.showlegend = False

        # Combine: background first, then foreground on top
        fig = bg
        for trace in fg.data:
            fig.add_trace(trace)

    else:
        # No state selected — show all counties at full opacity
        fig = px.scatter_ternary(
            df,
            a="nixon_share",
            b="humphrey_share",
            c="wallace_share",
            color="Rank",
            color_discrete_map=color_map,
            hover_name="county",
            hover_data={
                "nixon_share": ":.1%",
                "humphrey_share": ":.1%",
                "wallace_share": ":.1%"
            }
        )
        for trace in fig.data:
            trace.marker.opacity = 0.6
            trace.showlegend = False

    fig.update_layout(
        title="Nixon / Humphrey / Wallace Vote Share",
        font=dict(family="Playfair Display, serif", color="#1a1a1a"),
        paper_bgcolor="#f9f7f4",
    plot_bgcolor="#f9f7f4",
        showlegend=False,
        ternary=dict(
            aaxis=dict(title="Nixon"),
            baxis=dict(title="Humphrey"),
            caxis=dict(title="Wallace")
        )
    )

    return fig


@app.callback(
    Output("summary-bar", "figure"),
    Input("map-level", "data"),
    Input("current-state-fips", "data")
)
def update_summary_bar(level, state_fips):

    if level == "county" and state_fips is not None:
        source_df = df[df["fips"].str[:2] == state_fips]
        title = "County Type Counts"
    else:
        source_df = df
        title = "County Type Counts"

    county_counts = (
        source_df["Rank"]
        .value_counts()
        .reindex(["RD", "DR", "RI", "DI", "IR", "ID"], fill_value=0)
        .reset_index()
    )
    county_counts.columns = ["Rank", "Count"]
    county_counts = county_counts.sort_values(by="Count", ascending=False)

    fig = px.bar(
        county_counts,
        x="Rank",
        y="Count",
        color="Rank",
        color_discrete_map=color_map,
        title=title
    )

    for trace in fig.data:
        rank_name = trace.name
        outline_color = color_map_outline.get(rank_name, "black")
        trace.marker.line.color = outline_color
        trace.marker.line.width = 4

    fig.update_layout(showlegend=False, font=dict(family="Playfair Display, serif", color="#1a1a1a"), 
    paper_bgcolor="#f9f7f4",
    plot_bgcolor="#f9f7f4")
    return fig


@app.callback(
    Output("back-btn", "style"),
    Input("map-level", "data")
)
def toggle_back_button(level):
    base = {
        "position": "absolute",
        "top": "12px",
        "left": "12px",
        "zIndex": 999,
        "padding": "6px 14px",
        "background": "#1a1a2e",
        "color": "white",
        "border": "none",
        "borderRadius": "6px",
        "cursor": "pointer",
        "fontWeight": "bold",
        "fontSize": "14px",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.4)"
    }
    base["display"] = "block" if level == "county" else "none"
    return base


# Add map-level to the Output list
@app.callback(
    Output("county-map", "figure"),
    Output("map-level", "data"),
    Output("current-state-fips", "data"),
    Output("current-state-name", "data"),# ← ADD THIS

    Output("legend-rd", "style"),
    Output("legend-dr", "style"),
    Output("legend-ri", "style"),
    Output("legend-di", "style"),
    Output("legend-ir", "style"),
    Output("legend-id", "style"),

    Input("legend-rd", "n_clicks"),
    Input("legend-dr", "n_clicks"),
    Input("legend-ri", "n_clicks"),
    Input("legend-di", "n_clicks"),
    Input("legend-ir", "n_clicks"),
    Input("legend-id", "n_clicks"),
    Input("county-map", "clickData"),
    Input("back-btn", "n_clicks"),

    State("map-level", "data"), 
    State("current-state-fips", "data"),
    State("current-state-name", "data")
)
def toggle_layers(rd, dr, ri, di, ir, id_, clickData, back_clicks, level, current_state_fips, current_state_name):

    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"]
    if "back-btn" in trigger:
        fig = copy.deepcopy(state_map_fig)
        fig.update_layout(showlegend=False, font=dict(family="Playfair Display, serif", color="#1a1a1a"), paper_bgcolor="#f9f7f4",
    plot_bgcolor="#f9f7f4")
        new_level = "state"
        new_state_fips = None
        clicks = {"RD": rd, "DR": dr, "RI": ri, "DI": di, "IR": ir, "ID": id_}
        visibility = {k: (v or 0) % 2 == 0 for k, v in clicks.items()}
        for trace in fig.data:
            if trace.legendgroup in visibility:
                trace.visible = visibility[trace.legendgroup]
        def legend_style(is_visible):
            return {
                "display": "flex", "alignItems": "center",
                "cursor": "pointer", "marginBottom": "6px", "gap": "8px",
                "opacity": 1.0 if is_visible else 0.35,
                "color": "black" if is_visible else "#888"
            }
        styles = [legend_style(visibility[k]) for k in clicks]
        return fig, new_level, new_state_fips, None, *styles

    # ── Drill down: state click → county map ──────────────────────────────
    if "county-map.clickData" in trigger and level == "state":

        state_abbrev = clickData["points"][0]["location"]  # e.g. "CA"
        new_state_name = clickData["points"][0].get("hovertext", state_abbrev)

        # Reverse-lookup: abbrev → 2-digit FIPS string
        abbrev_to_fips = {v: k for k, v in fips_to_state.items()}
        state_fips = abbrev_to_fips.get(state_abbrev)

        if state_fips is None:
            fig = copy.deepcopy(state_map_fig)
            fig.update_layout(showlegend=False, font=dict(family="Playfair Display, serif", color="#1a1a1a"), 
                                 paper_bgcolor="#f9f7f4",plot_bgcolor="#f9f7f4")
            new_level = "state"
            new_state_fips = None
            new_state_name = None
        else:
            counties = df[df["fips"].str[:2] == state_fips]

            fig = px.choropleth(
                counties,
                geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
                locations="fips",
                color="Rank",
                scope="usa",
                color_discrete_map=color_map,
                hover_name="county",
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(showlegend=False, font=dict(family="Playfair Display, serif", color="#1a1a1a"),paper_bgcolor="#f9f7f4",
    plot_bgcolor="#f9f7f4")
            new_level = "county"  # ← now we're at county level
            new_state_fips = state_fips

    # ── Already at county level, or legend toggle ─────────────────────────
    elif "county-map.clickData" in trigger and level == "county":
        new_state_name = current_state_name  
            # County was clicked — rebuild the same state map so we stay put
        #counties = df[df["fips"].str[:2] == current_state_fips]
        fig = build_county_fig(current_state_fips)   # ← use helper
        new_level = "county"
        new_state_fips = current_state_fips  


    else:
        if level == "state" or current_state_fips is None:
            fig = copy.deepcopy(state_map_fig)
        else:
            fig = build_county_fig(current_state_fips)   # ← use helper

        #fig.update_layout(showlegend=False)
        new_level = level
        new_state_fips = current_state_fips
        new_state_name = current_state_name
        #fig = copy.deepcopy(state_map_fig) if level == "state" else copy.deepcopy(map_fig)
        #new_level = level  # unchanged

    # ── Legend toggling (applies to whichever fig we built) ───────────────
    clicks = {"RD": rd, "DR": dr, "RI": ri, "DI": di, "IR": ir, "ID": id_}
    visibility = {k: (v or 0) % 2 == 0 for k, v in clicks.items()}

    for trace in fig.data:
        if trace.legendgroup in visibility:
            trace.visible = visibility[trace.legendgroup]

    def legend_style(is_visible):
        return {
            "display": "flex", "alignItems": "center",
            "cursor": "pointer", "marginBottom": "6px", "gap": "8px",
            "opacity": 1.0 if is_visible else 0.35,
            "color": "black" if is_visible else "#888"
        }

    styles = [legend_style(visibility[k]) for k in clicks]

    return fig, new_level,new_state_fips, new_state_name, *styles  # ← note new_level added


def build_county_fig(state_fips):
    counties = df[df["fips"].str[:2] == state_fips]
    fig = px.choropleth(
        counties,
        geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
        locations="fips",
        color="Rank",
        scope="usa",
        color_discrete_map=color_map,
        hover_name="county",
    )
    for trace in fig.data:
        trace.legendgroup = trace.name
    fig.update_layout(showlegend=False, font=dict(family="Playfair Display, serif", color="#1a1a1a"), paper_bgcolor="#f9f7f4",
    plot_bgcolor="#f9f7f4")

    fig = add_dot_overlays(fig, counties)   # ← add dots
    fig.update_geos(fitbounds="locations", visible=False)

    return fig




@app.callback(
    Output("county-bar", "figure"),
    Input("county-map", "clickData")
)

def update_bar(clickData):

    if clickData is None:
        return px.bar(title="Click a county")

    county_fips = clickData["points"][0]["location"]
    print(county_fips)
    print(type(county_fips))
    
    candidates, votes, county_name = fetch_results(county_fips)

    # Original names for mapping
    original_names = candidates.copy()

    # Split names into two lines for display
    def two_line(name):
        parts = name.split()
        return parts[0] + "<br>" + " ".join(parts[1:])

    display_labels = [two_line(n) for n in candidates]

    # Map candidate colors
    color_map = {
        "Richard Nixon": "#E81B23",
        "Hubert Humphrey": "#4575b4",
        "George Wallace": "#00ff00"
    }

    # Create DataFrame
    vote_df = pd.DataFrame({
        "Candidate": original_names,      # used for coloring
        "Votes": votes,
        "Display": display_labels         # used for x-axis labels
    })

    # Create bar chart
    fig = px.bar(
        vote_df,
        x="Candidate",                    # keep original names here for color mapping
        y="Votes",
        color="Candidate",
        color_discrete_map=color_map
    )

    # Replace x-axis labels with two-line display
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=vote_df["Candidate"],
            ticktext=vote_df["Display"],
            tickangle=0
        ),
        title_text = county_name, title_x = 0.5,
        showlegend=False, # optional, 
        font=dict(family="Playfair Display, serif", color="#1a1a1a"),   paper_bgcolor="#f9f7f4",
    plot_bgcolor="#f9f7f4")

    return fig


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))