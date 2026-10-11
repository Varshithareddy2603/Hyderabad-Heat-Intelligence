import numpy as np
import pandas as pd

def make_demo_data(seed=17):
    """Synthetic data for interface demonstration only; not real city measurements."""
    rng=np.random.default_rng(seed)
    specs=[("Central Business District",37,12,78),("Dense Residential",35,18,65),
           ("Industrial Zone",38,7,86),("Park District",32,48,35),("Lakeside",33,39,42),
           ("Outer Suburb",34,27,52),("University Area",33,35,48),("Market District",36,14,75)]
    dates=pd.date_range("2025-04-01", periods=14, freq="D")
    rows=[]
    for area,temp,veg,built in specs:
        for i,date in enumerate(dates):
            rows.append({"area":area,"date":date,"temperature_c":round(temp+2*np.sin(i/3)+rng.normal(0,.8),1),
                         "vegetation_pct":float(np.clip(veg+rng.normal(0,2),0,100)),
                         "built_up_pct":float(np.clip(built+rng.normal(0,2),0,100)),
                         "humidity_pct":float(np.clip(48+rng.normal(0,8),15,95)),
                         "data_status":"SYNTHETIC DEMO"})
    return pd.DataFrame(rows)

def prepare_data(raw):
    df=raw.copy()
    aliases={"area":["area","neighborhood","district","location","name"],
      "date":["date","datetime","timestamp","time"],
      "temperature_c":["temperature_c","temp_c","temperature","air_temperature_c","lst_c"],
      "vegetation_pct":["vegetation_pct","ndvi_pct","green_cover_pct","vegetation"],
      "built_up_pct":["built_up_pct","impervious_pct","built_cover_pct","built_up"],
      "humidity_pct":["humidity_pct","relative_humidity","humidity"]}
    lower={str(c).strip().lower():c for c in df.columns}
    ren={}
    for target, opts in aliases.items():
        for opt in opts:
            if opt in lower:
                ren[lower[opt]]=target
                break
    df=df.rename(columns=ren)
    if "temperature_c" not in df.columns:
        raise ValueError("CSV must include a temperature column, such as temperature_c.")
    if "area" not in df.columns: df["area"]="All areas"
    df["date"]=pd.to_datetime(df["date"],errors="coerce") if "date" in df.columns else pd.NaT
    for col in ["temperature_c","vegetation_pct","built_up_pct","humidity_pct"]:
        if col not in df.columns: df[col]=np.nan
        df[col]=pd.to_numeric(df[col],errors="coerce")
    return df.dropna(subset=["temperature_c"])

def summarize(df):
    aggs={"temperature_c":["mean","min","max","count"]}
    for col in ["vegetation_pct","built_up_pct","humidity_pct"]:
        if df[col].notna().any(): aggs[col]="mean"
    out=df.groupby("area",dropna=False).agg(aggs)
    out.columns=["_".join(str(v) for v in col if v).strip("_") for col in out.columns.to_flat_index()]
    out=out.reset_index().sort_values("temperature_c_mean",ascending=False)
    return out.rename(columns={"temperature_c_mean":"mean_temp_c","temperature_c_min":"min_temp_c",
      "temperature_c_max":"max_temp_c","temperature_c_count":"observation_count",
      "vegetation_pct_mean":"mean_vegetation_pct","built_up_pct_mean":"mean_built_up_pct",
      "humidity_pct_mean":"mean_humidity_pct"})
