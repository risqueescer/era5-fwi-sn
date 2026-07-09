import os
import xarray as xr

from utils import get_last_date, remove_file, create_mask, save_netcdf # generics utils
from era5_io import ERA5IO # input/output
from paths import DataPaths

# ---------------------------------------------------------
# Variable mapping
# ---------------------------------------------------------
VAR_MAP = {
    "sd": "SWE",
    "t2m": "T2m",
    "d2m": "TD2m",
    "tp": "PRCP",
    "u10": "UU",
    "v10": "VV",
    "sf": "SF",
    "rsn": "RSN",
    "sp": "SP",
    "ssr": "SSR",
}


# ---------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------
def run_masking(config,years):

    # -----------------------------
    # Setup
    # -----------------------------
    io = ERA5IO()
    paths = DataPaths()
    
    # Day lag
    day_lag = config["era5_download"]["day_lag"]
    
    # Shapefile and mask
    shp_path = paths.shp_path()
    reference_nc = paths.raw_hourly('t2m',years[0],1)
    
    
    # Variables
    lst_v = config["era5_download"]["variables"]
    
    # ---------------------------------------------------------
    # MASK (centralized via utils)
    # ---------------------------------------------------------
    mask = create_mask(
        shp_path=shp_path,
        reference_nc=reference_nc,
        lat_name="lat",
        lon_name="lon"
    )

    # ---------------------------------------------------------
    # TIME RANGE
    # ---------------------------------------------------------
    last_date = get_last_date(day_lag)
    
    # -----------------------------
    # LOOP VARIABLES
    # -----------------------------
    for v in lst_v:

        v_hourly = VAR_MAP.get(v, v.upper())

        for y in years:

            m_end = last_date.month if y == last_date.year else 12
            m_range = range(1, m_end + 1)

            for m in m_range:

                # -------------------------------------------------
                # INPUT FILE
                # -------------------------------------------------
                i_download_path = paths.raw_hourly(v, y, m)
                
                if not os.path.exists(i_download_path):
                    print(f"[SKIP] missing input: {i_download_path}")
                    continue
                
                # -------------------------------------------------
                # OUTPUT FILE
                # -------------------------------------------------
                out_path = paths.masked_hourly(v_hourly, y, m)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_file_name = out_path.name
                # -------------------------------------------------
                # REMOVE CURRENT MONTH IF RE-RUN
                # -------------------------------------------------
                if y == last_date.year:
                    remove_file(out_path)
                    
                # -------------------------------------------------
                # SKIP IF EXISTS
                # -------------------------------------------------
                if os.path.exists(out_path):
                    continue

                print(f"[MASK] {out_file_name}")

                # -------------------------------------------------
                # LOAD + FORMAT
                # -------------------------------------------------
                ds = xr.open_dataset(i_download_path).load()
                # optional formatting (keep if needed)
                ds = io.format_ds(ds)

                print(f"Creating: {out_file_name}")
                
                # -------------------------------------------------
                # MASK APPLICATION
                # -------------------------------------------------
                ds_masked = io.apply_mask(
                    ds,
                    mask
                )
                # -------------------------------------------------
                # UNIT CONVERSIONS
                # -------------------------------------------------
                if v in ["sd", "tp", "sf", "sm"]:
                    ds_masked[v] = ds_masked[v] * 1000
                    ds_masked[v].attrs["units"] = "mm"

                elif v in ["t2m", "d2m"]:
                    ds_masked[v] = ds_masked[v] - 273.15
                    ds_masked[v].attrs["units"] = "°C"

                elif v == "sp":
                    ds_masked[v] = ds_masked[v] / 100.0
                    ds_masked[v].attrs["units"] = "hPa"

                elif v == "ssr":
                    ds_masked[v] = ds_masked[v] / 3600.0
                    ds_masked[v].attrs["units"] = "W m**-2"

                
                # -------------------------------------------------
                # FORMAT AND SAVE
                # -------------------------------------------------
                # Convert longitudes to negative if >=180
                ds_masked = io.format_longitudes(ds_masked)
                # Save as NetCDF file
                ds_masked = io.format_and_save(
                    ds=ds_masked,
                    variable_raw=v,
                    variable_final=v_hourly,
                    frequency="hourly",
                    config=config,
                    out_path=out_path,
                    save_netcdf_func=save_netcdf,
                )
                
                ds_masked.close()

                

    print("MASKING COMPLETED")