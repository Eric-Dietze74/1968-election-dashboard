import plotly.express as px

import shapefile  # PyShp
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape

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

df = pd.read_csv("missouri_1968.csv")

gdf2 = df.merge(gdf, right_on="GEOID", left_on="FIPS", how="left")

def state_map(df = df, state_name = "Missouri", gdf2 = gdf2):
    #df = import_state_data(state_name)
    gdf = df.merge(gdf2, right_on="GEOID", left_on="FIPS", how="left")

    color_map = {
    "RD": "#E81B23",  # Republican → Democrat
    "DR": "#4575b4",
    "RI": "#E81B23",
    "IR": "#00ff00",
    "DI": "#4575b4",
    "ID": "#00ff00"}

    fig = px.choropleth(
        df,
        geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
        locations="FIPS",
        color="Rank",
        scope="usa",
        color_discrete_map=color_map,
        category_orders={"Rank": sorted(df["Rank"].unique())},
        hover_name= "County_County",
        title="County Labels by FIPS"
    )

    gdf2["lon"] = gdf2["geometry"].apply(lambda geom: geom.centroid.x if geom is not None else None)
    gdf2["lat"] = gdf2["geometry"].apply(lambda geom: geom.centroid.y if geom is not None else None)

    ri_df = gdf2[gdf2["Rank"] == "RI"]

    di_df = gdf2[gdf2["Rank"] == "DI"]

    ir_df = gdf2[gdf2["Rank"] == "IR"]


    fig.add_scattergeo(
        lon=ri_df["lon"],
        lat=ri_df["lat"],
        mode="markers",
        marker=dict(
            size=5,
            color="#00ff00",
            opacity=0.8
        ),
        name="RI pattern",
        hoverinfo="skip" 
    )

    fig.add_scattergeo(
        lon=di_df["lon"],
        lat=di_df["lat"],
        mode="markers",
        marker=dict(
            size=5,
            color="#00ff00",
            opacity=0.8
        ),
        name="DI pattern",
        hoverinfo="skip" 
    )


    fig.add_scattergeo(
        lon=ir_df["lon"],
        lat=ir_df["lat"],
        mode="markers",
        marker=dict(
            size=5,
            color="red",
            opacity=0.8
        ),
        name="IR pattern",
        hoverinfo="skip" 
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(showlegend=False)
    fig.show()
    
    
state_map()