import requests
import pandas as pd
import plotly.express as px
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.analysis import make_demo_data, prepare_data, summarize

st.set_page_config(page_title="Hyderabad Heat Intelligence | Varshitha Reddy", page_icon="🌡️", layout="wide")

# Dark, high-contrast portfolio styling
st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: radial-gradient(ellipse at 12% 0%, #142a3a 0%, #0b1220 42%, #080d17 100%); color: #e7edf7; }
[data-testid="stHeader"] { background: rgba(8,13,23,.88); }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#101b2b,#0a111d); border-right: 1px solid #26364a; }
.block-container { padding-top: 1.6rem; max-width: 1500px; }
.hero { padding: 1.6rem 1.8rem; border: 1px solid #29445a; border-radius: 20px; background: linear-gradient(115deg,rgba(22,54,75,.96),rgba(14,24,42,.94) 60%,rgba(20,39,59,.96)); margin-bottom: 1rem; box-shadow: 0 14px 40px rgba(0,0,0,.20); }
.eyebrow { color: #55e6c1; letter-spacing: .16em; font-size: .76rem; font-weight: 800; text-transform: uppercase; }
.hero h1 { color: #f4f8ff; font-size: clamp(1.8rem,3.4vw,3rem); line-height: 1.12; margin: .4rem 0 .55rem 0; }
.hero p { color: #b5c5d9; margin: 0; font-size: 1rem; }
[data-testid="stMetric"] { background: linear-gradient(145deg,#142338,#101a2a); border: 1px solid #2a3e55; padding: 16px 18px; border-radius: 15px; box-shadow: 0 8px 22px rgba(0,0,0,.16); }
[data-testid="stMetricLabel"] { color: #9db2c9 !important; }
[data-testid="stMetricValue"] { color: #f4f8ff !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: #293a50 !important; }
h2,h3 { color: #eaf3ff; }
.stCaption, [data-testid="stCaptionContainer"] { color: #9fb1c7; }
.stButton>button, .stDownloadButton>button { border-radius: 10px; border: 1px solid #2b9f9a; background: #123d46; color: #e8fffb; }
.stButton>button:hover, .stDownloadButton>button:hover { border-color: #55e6c1; color: white; }
hr { border-color: #26364a; }
</style>
<div class="hero"><div class="eyebrow">URBAN CLIMATE • LIVE WEATHER INTELLIGENCE</div><h1>Hyderabad Heat Intelligence</h1><p>Explore neighborhood-level weather estimates, identify relative hotspots, and compare heat indicators across the city.</p><p style="margin-top:.8rem;color:#55e6c1;font-weight:600">A data analytics portfolio project by Varshitha Reddy</p></div>
""", unsafe_allow_html=True)
CITY_POINTS = [
    {"area": "HITEC City", "lat": 17.4435, "lon": 78.3772},
    {"area": "Charminar", "lat": 17.3616, "lon": 78.4747},
    {"area": "Secunderabad", "lat": 17.4399, "lon": 78.4983},
    {"area": "Gachibowli", "lat": 17.4401, "lon": 78.3489},
    {"area": "LB Nagar", "lat": 17.3457, "lon": 78.5522},
    {"area": "Kukatpally", "lat": 17.4849, "lon": 78.4138},
    {"area": "Rajendra Nagar", "lat": 17.3200, "lon": 78.4030},
    {"area": "Uppal", "lat": 17.4058, "lon": 78.5591},
    {"area": "Banjara Hills", "lat": 17.4126, "lon": 78.4482},
    {"area": "Miyapur", "lat": 17.4968, "lon": 78.3568},
]
API_URL = "https://api.open-meteo.com/v1/forecast"

st.caption("INTERACTIVE CITY MAP  /  EXPLORATORY ANALYTICS  /  TRANSPARENT DATA PROVENANCE")
st.info("**Data transparency:** Live mode retrieves current weather model data from Open-Meteo for representative coordinates. These are point-level model estimates, not street-level sensor measurements. The built-in historical dataset is synthetic demo data. Heat categories are an illustrative screening aid, not official health warnings.")

@st.cache_data(ttl=600, show_spinner=False)
def fetch_point(point):
    params = {
        "latitude": point["lat"], "longitude": point["lon"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
        "timezone": "Asia/Kolkata"
    }
    response = requests.get(API_URL, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()
    cur = payload.get("current")
    if not cur:
        raise ValueError("The weather API did not return current conditions.")
    return {
        **point,
        "temperature_c": cur.get("temperature_2m"),
        "humidity_pct": cur.get("relative_humidity_2m"),
        "apparent_temperature_c": cur.get("apparent_temperature"),
        "precipitation_mm": cur.get("precipitation"),
        "wind_speed_kmh": cur.get("wind_speed_10m"),
        "weather_code": cur.get("weather_code"),
        "observed_at_local": cur.get("time"),
        "data_status": "LIVE API MODEL ESTIMATE",
    }

def build_blended_heat_map(df, metric="apparent_temperature_c"):
    """Create a softly blended heat surface from representative point estimates."""
    # Explicitly use the public OpenStreetMap tile endpoint, not a commercial
    # Mapbox/Carto/Google provider that may ask for an API key.
    # The tile service needs internet access but no API key.
    m = folium.Map(location=[17.3850, 78.4867], zoom_start=11, tiles=None, control_scale=True)
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
        name="OpenStreetMap (no API key)",
        overlay=False,
        control=True,
        max_zoom=19,
    ).add_to(m)
    dark_tiles_css = folium.Element("""
    <style>
      .leaflet-tile-pane {
        filter: invert(0.88) hue-rotate(180deg) brightness(0.72) contrast(0.92) saturate(0.62);
      }
    </style>
    """)
    m.get_root().header.add_child(dark_tiles_css)
    valid = df.dropna(subset=["lat", "lon", metric]).copy()
    if not valid.empty:
        values = valid[metric].astype(float)
        low, high = float(values.min()), float(values.max())
        spread = max(high - low, 0.1)
        # Normalize intensity while keeping all sites visible, including the coolest green locations.
        points = [[float(r.lat), float(r.lon), 0.35 + 0.65 * ((float(getattr(r, metric)) - low) / spread)] for r in valid.itertuples()]
        HeatMap(points, radius=42, blur=34, min_opacity=0.22, max_zoom=14,
                gradient={0.0: "#22c55e", 0.35: "#a3e635", 0.62: "#facc15", 0.82: "#ef4444", 1.0: "#991b1b"}).add_to(m)
        for _, r in valid.iterrows():
            folium.CircleMarker([r["lat"], r["lon"]], radius=3, color="#eaf2ff", weight=1,
                fill=True, fill_color="#eaf2ff", fill_opacity=0.8,
                tooltip=f"{r['area']}: {float(r[metric]):.1f} °C").add_to(m)
    return m


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weekly_forecast():
    response = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": 17.3850, "longitude": 78.4867,
        "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min",
        "timezone": "Asia/Kolkata", "forecast_days": 7
    }, timeout=15)
    response.raise_for_status()
    payload = response.json().get("daily", {})
    return pd.DataFrame({
        "date": pd.to_datetime(payload.get("time", [])),
        "min_temp_c": payload.get("temperature_2m_min", []),
        "max_temp_c": payload.get("temperature_2m_max", []),
        "min_feels_c": payload.get("apparent_temperature_min", []),
        "max_feels_c": payload.get("apparent_temperature_max", []),
    })


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_point_weekly_forecast(point):
    """Fetch daily forecast for one representative Hyderabad location."""
    response = requests.get(API_URL, params={
        "latitude": point["lat"], "longitude": point["lon"],
        "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min",
        "timezone": "Asia/Kolkata", "forecast_days": 7
    }, timeout=15)
    response.raise_for_status()
    daily = response.json().get("daily", {})
    return pd.DataFrame({
        "date": pd.to_datetime(daily.get("time", [])),
        "map_air_max_c": daily.get("temperature_2m_max", []),
        "map_air_min_c": daily.get("temperature_2m_min", []),
        "map_feels_max_c": daily.get("apparent_temperature_max", []),
        "map_feels_min_c": daily.get("apparent_temperature_min", []),
    })


def heat_screen(temp):
    # Illustrative apparent-temperature bands for exploratory visualization only.
    if pd.isna(temp): return "Unknown"
    if temp < 27: return "Lower"
    if temp < 32: return "Elevated"
    if temp < 39: return "High"
    return "Very high"

with st.sidebar:
    st.header("Data controls")
    mode = st.radio("Choose data source", ["Live Hyderabad weather", "Synthetic demo history", "Upload CSV"])
    st.caption("Live readings are cached for 10 minutes. Use Refresh data to request a new update after the cache expires.")
    if st.button("🔄 Refresh live data", disabled=(mode != "Live Hyderabad weather")):
        fetch_point.clear()
        st.rerun()

if mode == "Live Hyderabad weather":
    with st.spinner("Fetching current weather estimates for Hyderabad locations…"):
        rows, errors = [], []
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(fetch_point, p): p for p in CITY_POINTS}
            for future in as_completed(futures):
                try: rows.append(future.result())
                except Exception as exc: errors.append(f"{futures[future]['area']}: {exc}")
    if not rows:
        st.error("Could not retrieve live weather. Check your internet connection and try again. The API may be temporarily unavailable.")
        if errors: st.code("\n".join(errors[:3]))
        st.stop()
    df = pd.DataFrame(rows).sort_values("area")
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    df["heat_screen"] = df["apparent_temperature_c"].apply(heat_screen)
    df["date"] = pd.to_datetime(df["observed_at_local"], errors="coerce")
    if errors:
        st.warning(f"Live data loaded for {len(rows)} of {len(CITY_POINTS)} locations; {len(errors)} locations failed. Missing points are omitted.")
    stamp = ", ".join(sorted(df["observed_at_local"].dropna().astype(str).unique()))
    st.caption(f"Source: Open-Meteo current weather API · Local observation/model timestamp(s): {stamp or 'not supplied'} · Refresh cache: 10 minutes")
    metric_temp = df["temperature_c"].mean()
    metric_feels = df["apparent_temperature_c"].mean()
    hot_row = df.sort_values("apparent_temperature_c", ascending=False).iloc[0]
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Mean air temperature", f"{metric_temp:.1f} °C")
    m2.metric("Mean feels-like temperature", f"{metric_feels:.1f} °C")
    m3.metric("Highest feels-like estimate", f"{hot_row['apparent_temperature_c']:.1f} °C", str(hot_row["area"]))
    m4.metric("Locations returned", f"{len(df)} / {len(CITY_POINTS)}")
    st.subheader("🌡️ Hyderabad blended heat map")
    st.write("The dark map uses a soft, blended green-to-red heat shade. Choose a forecast weekday below and the map colors update to that day's forecast at each representative location.")
    colors = {"Lower":"#22c55e", "Elevated":"#a3e635", "High":"#ef4444", "Very high":"#b91c1c", "Unknown":"#94a3b8"}
    try:
        with st.spinner("Loading 7-day forecasts for map locations…"):
            forecast_frames = []
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = {pool.submit(fetch_point_weekly_forecast, point): point for point in CITY_POINTS}
                for future in as_completed(futures):
                    point = futures[future]
                    try:
                        forecast = future.result()
                        forecast["area"] = point["area"]
                        forecast_frames.append(forecast)
                    except Exception:
                        pass
        if not forecast_frames:
            raise RuntimeError("No location forecasts were returned")
        city_forecasts = pd.concat(forecast_frames, ignore_index=True)
        city_forecasts["weekday"] = city_forecasts["date"].dt.day_name()
        available_days = city_forecasts[["date", "weekday"]].drop_duplicates().sort_values("date")
        selected_day = st.selectbox("Choose forecast weekday (updates the map)", available_days["weekday"].tolist(), index=0, key="heatmap_weekday")
        selected_date = available_days.loc[available_days["weekday"] == selected_day, "date"].iloc[0]
        day_map_data = city_forecasts[city_forecasts["date"] == selected_date].merge(df[["area", "lat", "lon"]], on="area", how="left")
        map_metric = st.radio("Shade the map by", ["Feels-like temperature", "Air temperature"], horizontal=True)
        metric_col = "map_feels_max_c" if map_metric == "Feels-like temperature" else "map_air_max_c"
        day_map_data["heat_screen"] = day_map_data[metric_col].apply(heat_screen)
        heat_map = build_blended_heat_map(day_map_data, metric_col)
        st_folium(heat_map, use_container_width=True, height=560, returned_objects=[])
        st.markdown("<div style='display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:.9rem'><b>Temperature shading:</b><span style='color:#22c55e'>● Lower / cool</span><span style='color:#a3e635'>● Mild</span><span style='color:#facc15'>● Warmer</span><span style='color:#ef4444'>● Hot</span><span style='color:#991b1b'>● Highest</span></div>", unsafe_allow_html=True)
        st.caption(f"Map shows forecast daily maximum {map_metric.lower()} for {selected_day}, {selected_date.strftime('%d %b %Y')}. Smooth shading is interpolated from representative Open-Meteo forecast points, not street-level measurements.")
    except Exception as exc:
        st.warning(f"Location-specific weekday forecasts are temporarily unavailable; showing current readings on the map. Details: {exc}")
        map_metric = st.radio("Shade the map by", ["Feels-like temperature", "Air temperature"], horizontal=True, key="fallback_map_metric")
        metric_col = "apparent_temperature_c" if map_metric == "Feels-like temperature" else "temperature_c"
        heat_map = build_blended_heat_map(df, metric_col)
        st_folium(heat_map, use_container_width=True, height=560, returned_objects=[])

    st.subheader("📅 Weekday temperature analysis")
    st.caption("The selected weekday above controls the heat map. Forecast values are model estimates, not historical observations.")
    try:
        weekly = fetch_weekly_forecast()
        if not weekly.empty:
            weekly["weekday"] = weekly["date"].dt.day_name()
            chosen = weekly.loc[weekly["weekday"] == selected_day].iloc[0] if "selected_day" in locals() and (weekly["weekday"] == selected_day).any() else weekly.iloc[0]
            day_a, day_b, day_c, day_d = st.columns(4)
            day_a.metric("Date", chosen["date"].strftime("%d %b %Y"))
            day_b.metric("Minimum air temp", f"{chosen['min_temp_c']:.1f} °C")
            day_c.metric("Maximum air temp", f"{chosen['max_temp_c']:.1f} °C")
            day_d.metric("Maximum feels-like", f"{chosen['max_feels_c']:.1f} °C")
            weekly_chart = weekly.melt(id_vars=["date", "weekday"], value_vars=["min_temp_c", "max_temp_c", "min_feels_c", "max_feels_c"], var_name="measure", value_name="temperature_c")
            weekly_chart["measure"] = weekly_chart["measure"].map({"min_temp_c":"Minimum air", "max_temp_c":"Maximum air", "min_feels_c":"Minimum feels-like", "max_feels_c":"Maximum feels-like"})
            st.plotly_chart(px.line(weekly_chart, x="weekday", y="temperature_c", color="measure", markers=True, template="plotly_dark", labels={"weekday":"Forecast weekday", "temperature_c":"Temperature (°C)", "measure":"Measure"}), use_container_width=True)
        else:
            st.info("The forecast API did not return daily values.")
    except Exception as exc:
        st.warning(f"Weekday forecast is temporarily unavailable: {exc}")
    left,right = st.columns(2)
    with left:
        st.subheader("Feels-like temperature by location")
        bar = df.sort_values("apparent_temperature_c", ascending=False)
        st.plotly_chart(px.bar(bar, template="plotly_dark", x="apparent_temperature_c", y="area", orientation="h", color="heat_screen", color_discrete_map=colors,
            labels={"apparent_temperature_c":"Feels-like temperature (°C)","area":"Location","heat_screen":"Screening band"}), use_container_width=True)
    with right:
        st.subheader("Humidity vs. feels-like temperature")
        st.plotly_chart(px.scatter(df, template="plotly_dark", x="humidity_pct", y="apparent_temperature_c", color="heat_screen", color_discrete_map=colors,
            hover_name="area", labels={"humidity_pct":"Relative humidity (%)","apparent_temperature_c":"Feels-like temperature (°C)","heat_screen":"Screening band"}), use_container_width=True)
    st.subheader("Current location-level data")
    st.dataframe(df[["area","temperature_c","apparent_temperature_c","humidity_pct","wind_speed_kmh","precipitation_mm","heat_screen","observed_at_local","data_status"]].rename(columns={"area":"Location","temperature_c":"Air temp (°C)","apparent_temperature_c":"Feels-like (°C)","humidity_pct":"Humidity (%)","wind_speed_kmh":"Wind (km/h)","precipitation_mm":"Precipitation (mm)","heat_screen":"Screening band","observed_at_local":"API timestamp","data_status":"Data status"}), use_container_width=True, hide_index=True)
    st.download_button("Download live readings as CSV", df.to_csv(index=False).encode("utf-8"), "hyderabad_live_weather_estimates.csv", "text/csv")
    st.warning("Interpretation: apparent temperature is a weather-service estimate of how conditions may feel. These readings do not measure local land-surface temperature, neighborhood-level urban heat islands, or individual heat exposure. Screening bands here are illustrative and must not be treated as medical advice or official alerts.")

elif mode == "Synthetic demo history":
    df = prepare_data(make_demo_data())
    st.warning("SYNTHETIC DEMO DATA — these values are generated for practice and do not describe real Hyderabad weather.")
    areas = sorted(df["area"].astype(str).unique())
    selected = st.multiselect("Filter demo areas", areas, default=areas)
    df = df[df["area"].astype(str).isin(selected)]
    if df.empty: st.stop()
    summary = summarize(df)
    a,b,c,d = st.columns(4)
    a.metric("Demo observations", f"{len(df):,}")
    b.metric("Mean temperature", f"{df.temperature_c.mean():.1f} °C")
    c.metric("Warmest demo area", str(summary.iloc[0]["area"]))
    d.metric("Mean vegetation", f"{df.vegetation_pct.mean():.1f}%")
    left,right = st.columns(2)
    with left:
        at = df.groupby("area", as_index=False).temperature_c.mean().sort_values("temperature_c", ascending=False)
        st.plotly_chart(px.bar(at, template="plotly_dark", x="area", y="temperature_c", color="temperature_c", color_continuous_scale="YlOrRd", labels={"area":"Demo area","temperature_c":"Mean temperature (°C)"}), use_container_width=True)
    with right:
        st.plotly_chart(px.scatter(df, template="plotly_dark", x="vegetation_pct", y="temperature_c", color="built_up_pct", hover_name="area", labels={"vegetation_pct":"Vegetation (%)","temperature_c":"Temperature (°C)","built_up_pct":"Built-up (%)"}), use_container_width=True)
    trend = df.groupby("date", as_index=False).temperature_c.mean()
    st.plotly_chart(px.line(trend, template="plotly_dark", x="date", y="temperature_c", markers=True, labels={"date":"Date","temperature_c":"Mean demo temperature (°C)"}), use_container_width=True)
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.download_button("Download demo data as CSV", df.to_csv(index=False).encode("utf-8"), "synthetic_demo_data.csv", "text/csv")

else:
    uploaded = st.file_uploader("Upload a CSV containing temperature data", type=["csv"])
    st.caption("Required: a temperature column (for example temperature_c). Optional: area, date, vegetation_pct, built_up_pct, humidity_pct, lat, lon.")
    if uploaded is None:
        st.info("Upload a CSV to view its analytics.")
        st.stop()
    try:
        raw = pd.read_csv(uploaded)
        df = prepare_data(raw)
    except Exception as exc:
        st.error(f"Could not read this CSV: {exc}")
        st.stop()
    st.warning("Uploaded data is user-provided. Verify its source, units, location coordinates, and timestamp before interpreting results.")
    a,b,c = st.columns(3)
    a.metric("Rows", f"{len(df):,}")
    b.metric("Mean temperature", f"{df.temperature_c.mean():.1f} °C")
    c.metric("Areas", f"{df.area.nunique():,}")
    st.plotly_chart(px.bar(df.groupby("area", as_index=False).temperature_c.mean().sort_values("temperature_c", ascending=False), template="plotly_dark", x="area", y="temperature_c", color="temperature_c", color_continuous_scale="YlOrRd", labels={"area":"Area","temperature_c":"Mean temperature (°C)"}), use_container_width=True)
    if {"lat","lon"}.issubset(df.columns):
        geo = df.dropna(subset=["lat","lon"]).copy()
        if not geo.empty:
            st.subheader("Uploaded data map")
            uploaded_map = folium.Map(location=[float(geo["lat"].mean()), float(geo["lon"].mean())], zoom_start=10, tiles=None, control_scale=True)
            folium.TileLayer(
                tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attr='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
                name="OpenStreetMap (no API key)", overlay=False, control=True, max_zoom=19,
            ).add_to(uploaded_map)
            temps = pd.to_numeric(geo["temperature_c"], errors="coerce")
            low = float(temps.min()) if temps.notna().any() else 0.0
            high = float(temps.max()) if temps.notna().any() else 1.0
            spread = max(high - low, 0.1)
            heat_points = [[float(r["lat"]), float(r["lon"]), 0.35 + 0.65 * ((float(r["temperature_c"]) - low) / spread)] for _, r in geo.dropna(subset=["temperature_c"]).iterrows()]
            if heat_points:
                HeatMap(heat_points, radius=38, blur=30, min_opacity=0.2,
                        gradient={0.0: "#22c55e", 0.35: "#a3e635", 0.62: "#facc15", 0.82: "#ef4444", 1.0: "#991b1b"}).add_to(uploaded_map)
            for _, r in geo.dropna(subset=["temperature_c"]).iterrows():
                folium.CircleMarker([float(r["lat"]), float(r["lon"])], radius=3, color="#eaf2ff", weight=1,
                    fill=True, fill_color="#eaf2ff", fill_opacity=0.8,
                    tooltip=f"{r['area']}: {float(r['temperature_c']):.1f} °C").add_to(uploaded_map)
            st_folium(uploaded_map, use_container_width=True, height=500, returned_objects=[])
        else: st.info("Latitude/longitude columns exist, but no valid coordinates were found.")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Download cleaned CSV", df.to_csv(index=False).encode("utf-8"), "cleaned_uploaded_data.csv", "text/csv")

st.divider()
st.caption("Built with Streamlit, Plotly, pandas and the Open-Meteo API. Map pins are representative sample points; they are not official weather-station locations unless explicitly verified.")
