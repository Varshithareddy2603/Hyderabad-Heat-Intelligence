# Hyderabad Heat Intelligence — Varshitha Reddy

An interactive Streamlit portfolio project for exploring current weather estimates at representative Hyderabad locations, visualizing them on a street map, and comparing apparent temperature and humidity. It also includes a clearly labelled synthetic historical dataset for practicing time-series and vegetation analysis.

## Features

- Dark-mode analytics interface with an interactive dark basemap
- Switchable map layers for screening band, air temperature, feels-like temperature, humidity, and wind speed
- Relative hotspot ranking beside the map
- Marker size scales with feels-like temperature

- Interactive OpenStreetMap-based map with colored location markers
- Current air temperature, apparent (“feels-like”) temperature, humidity, wind speed, precipitation, and API timestamp
- Illustrative heat-screening bands based on apparent temperature
- Location comparison bar chart and humidity-versus-apparent-temperature scatter plot
- 10-minute API response cache and manual refresh button
- CSV download of current readings
- Separate synthetic demo history and user CSV upload modes
- Optional map for uploaded data when latitude and longitude columns are supplied

## Important data limitations

**Live mode is not a street-level sensor network.** It requests current conditions from the Open-Meteo API for a set of representative coordinates. The returned values are weather-model/API estimates for those points, not verified measurements from official stations at those exact locations. Map pins show the query coordinates, not the source's confirmed sensor locations.

The built-in historical data (`data/synthetic_demo_data.csv`) is **synthetic** and must not be reported as real Hyderabad measurements. The vegetation-versus-temperature chart only works as a demonstration with this generated dataset unless you provide a trustworthy real dataset.

The heat-screening bands are simplified, illustrative thresholds applied to apparent temperature. They are not official heat alerts, not a clinical heat index, and not medical advice. Do not use them for safety-critical decisions. Apparent temperature is not land-surface temperature and does not establish neighborhood heat-island intensity.

## Run on Windows with VS Code

1. Extract the project ZIP.
2. In VS Code, choose **File → Open Folder** and select the `Hyderabad-Heat-Intelligence` folder (the folder containing `app.py` and `requirements.txt`).
3. Open **Terminal → New Terminal**.
4. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   py -m streamlit run app.py
   ```

6. Select **Live Hyderabad weather** in the sidebar. Internet access is required for live mode. Select **Synthetic demo history** to explore generated sample data without relying on the weather API.

## Data source

- Live weather: [Open-Meteo API](https://open-meteo.com/). Review its current terms and attribution requirements before public deployment or commercial use.
- Street map tiles: explicit public OpenStreetMap tile URL, with no API key required. Map tiles still require internet access and are subject to OpenStreetMap tile usage policies.

## CSV upload

A temperature column is required (for example `temperature_c`). Optional columns include `area`, `date`, `vegetation_pct`, `built_up_pct`, `humidity_pct`, `lat`, and `lon`. Temperature is assumed to be in degrees Celsius; confirm units before upload. For mapped uploaded data, include valid numeric `lat` and `lon` columns.

## Suggested next improvements

- Add tests for input validation and heat-screening logic.
- Add an explicit source timestamp and API failure status to automated tests.
- Compare with verified local weather station observations where licensed data is available.
- Add historical daily observations from a documented source before making claims about long-term trends.
- Add deployment secrets only if a future data provider requires an API key; never commit credentials.

## Stack

Python · Streamlit · pandas · Plotly · Requests · OpenStreetMap · Open-Meteo
