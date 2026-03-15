import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State
import numpy as np
import shapefile  # PyShp
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import copy


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

for trace in state_map_fig.data:
    trace.legendgroup = trace.name
    
    
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
    marker=dict(size=5, color="#00ff00", opacity=0.8),
    legendgroup="RI",
    showlegend=False,
    hoverinfo="skip"
)

map_fig.add_scattergeo(
    lon=di_df["lon"],
    lat=di_df["lat"],
    mode="markers",
    marker=dict(size=5, color="#00ff00", opacity=0.8),
    legendgroup="DI",
    showlegend=False,
    hoverinfo="skip"
)

map_fig.add_scattergeo(
    lon=ir_df["lon"],
    lat=ir_df["lat"],
    mode="markers",
    marker=dict(size=5, color="red", opacity=0.8),
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

    df_slice = df[df["FIPS"] == county_fips]

    if df_slice.empty:
        print("No match for:", county_fips)
        return [], []

    row = df_slice.iloc[0]
    county_name = row.County_County

    results = {
        "Richard Nixon": row["richard_nixon_republican_num"],
        "Hubert Humphrey": row["hubert_humphrey_democratic_num"],
        "George Wallace": row["george_wallace_american_independent_num"]
    }

    results = dict(sorted(results.items(),
                          key=lambda x: x[1],
                          reverse=True))

    names = list(results.keys())
    numbers = np.array(list(results.values()))

    return names, numbers, county_name



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
    
    html.H1(
        id="dashboard-title",
        children="Select a State",
        style={
            "textAlign": "center",
            "marginTop": "10px"
        }
    ),

    # ===== TOP ROW =====
    html.Div([

        # COLUMN 1 — MAP
        html.Div([
            dcc.Graph(id="county-map", figure=state_map_fig)
        ], style={
            "width": "60%",
            "border": "2px solid black", 
            "margin-left": "50px"
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
        dcc.Graph(figure=summary_fig)
    ], style={
        "width": "65%",
        "marginTop": "20px"
    })

])



#I believe this will eventually be scrapped b/c this is the name of the dashboard, not the title of the chart. 
@app.callback(
    Output("dashboard-title", "children"),
    Input("county-map", "clickData")
)
def update_title(clickData):

    if clickData is None:
        return "Select a State"

    state_name = clickData["points"][0]["hovertext"].split(", ")[1]
    #print(clickData)
    return f"{state_name} Vote Total"


@app.callback(
    Output("county-map", "figure"),

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
    
    #new addins 
    Input("county-map", "clickData"),

    State("map-level", "data")
)
def toggle_layers(rd, dr, ri, di, ir, id_, clickData, level):

    #new add in 
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"]
    
    
    if "county-map.clickData" in trigger and level == "state":
        
        state_fips = clickData["points"][0]["location"]#[:2]
        counties = df[df["fips"].str[:2] == state_fips]
        
        fig = px.choropleth(
            counties,
            geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
            locations="fips",
            color="Rank",
            scope="usa",
            color_discrete_map=color_map)

    else:
            fig = copy.deepcopy(state_map_fig) if level == "state" else copy.deepcopy(map_fig)
    
    
    
    
    
    fig = copy.deepcopy(fig)

    clicks = {
        "RD": rd,
        "DR": dr,
        "RI": ri,
        "DI": di,
        "IR": ir,
        "ID": id_,
    }

    visibility = {
        k: (v or 0) % 2 == 0
        for k, v in clicks.items()
    }

    # toggle map traces
    for trace in fig.data:
        if trace.legendgroup in visibility:
            trace.visible = visibility[trace.legendgroup]

    # legend visual styles
    def legend_style(is_visible):
        return {
            "display": "flex",
            "alignItems": "center",
            "cursor": "pointer",
            "marginBottom": "6px",
            "gap": "8px",

            # 🔥 visual feedback
            "opacity": 1.0 if is_visible else 0.35,
            "color": "black" if is_visible else "#888"
        }

    styles = [legend_style(visibility[k]) for k in clicks]

    return fig, *styles



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
        showlegend=False  # optional
    )

    return fig


if __name__ == "__main__": 
    app.run(debug=False)