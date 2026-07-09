import os
import xarray as xr
from calendar import monthrange

from utils import get_last_date, remove_file, save_netcdf, is_current_year # generics utils
from era5_io import ERA5IO
from era5_derived_vars import DerivedVars  # calculate derived variables from hourly era5
from paths import DataPaths

# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------
DERIVED_VARS = ["WS", "WD", "RH", "RF", "SD"]


VAR_PATHS = {
    "T2m": "T2m",
    "TD2m": "TD2m",
    "PRCP": "PRCP",
    "SF": "SF",
    "SWE": "SWE",
    "RSN": "RSN",
    "UU": "UU",
    "VV": "VV",
}


# ---------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------
def run_derived_vars(config,years):
    io = ERA5IO()
    idx = DerivedVars()
    paths = DataPaths()
    # ---------------------------------------------------------
    # TIME
    # ---------------------------------------------------------
    day_lag = config["era5_download"]["day_lag"]
    last_date = get_last_date(day_lag)
    
    # ---------------------------------------------------------
    # MAIN LOOP
    # ---------------------------------------------------------
    for derived_var in DERIVED_VARS:
        
        
        for y in years:

            m_end = last_date.month if y == last_date.year else 12
            m_range = range(1, m_end + 1)

            for m in m_range:
                # -------------------------------------------------
                # OUTPUT FILE
                # -------------------------------------------------
                out_path = paths.masked_hourly(derived_var, y, m)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_file_name = out_path.name
                
                # -------------------------------------------------
                # TIME VALIDATION
                # -------------------------------------------------
                num_days = monthrange(y, m)[1]
                max_len_time = (
                    last_date.day * 24
                    if (y == last_date.year and m == last_date.month)
                    else num_days * 24
                )

                # -------------------------------------------------
                # CHECK EXISTING FILE
                # -------------------------------------------------
                if os.path.exists(out_path):
                    if not is_current_year(y,day_lag):
                        print(f"[OK] {out_file_name} (past year, existing)")
                        continue

                    try:
                        ds = xr.open_dataset(out_path).load()

                        if len(ds.time) != max_len_time:
                            ds.close()
                            os.remove(out_path)
                            print(f"[REBUILD] incomplete time {out_file_name}")
                            continue

                        print(f"[OK] {out_file_name}")
                        ds.close()
                        continue

                    except:
                        print(f"[CORRUPT] {out_file_name}")
                        remove_file(out_path)
                        continue

                # -------------------------------------------------
                # COMPUTE INPUT FILE PATHS
                # -------------------------------------------------
                paths_dict = {
                    "T2m": paths.masked_hourly('T2m', y, m),
                    "TD2m": paths.masked_hourly('TD2m', y, m),
                    "PRCP": paths.masked_hourly('PRCP', y, m),
                    "SF": paths.masked_hourly('SF', y, m),
                    "SWE": paths.masked_hourly('SWE', y, m),
                    "RSN": paths.masked_hourly('RSN', y, m),
                    "UU": paths.masked_hourly('UU', y, m),
                    "VV": paths.masked_hourly('VV', y, m),
                }
                

                # -------------------------------------------------
                # CHECK DEPENDENCIES
                # -------------------------------------------------
                if derived_var in ["RH"] and not (paths_dict["T2m"].exists() and paths_dict["TD2m"].exists()):
                    continue

                if derived_var in ["RF"] and not (paths_dict["SF"].exists() and paths_dict["PRCP"].exists()):
                    continue

                if derived_var in ["SD"] and not (paths_dict["SWE"].exists() and paths_dict["RSN"].exists()):
                    continue

                if derived_var in ["WS", "WD"] and not (paths_dict["UU"].exists() and paths_dict["VV"].exists()):
                    continue

                print(f"[COMPUTE] {out_file_name}")

                # -------------------------------------------------
                # COMPUTE INDICES
                # -------------------------------------------------
                if derived_var == "RH":
                    ds = idx.computeRH(paths_dict["T2m"], paths_dict["TD2m"],"T2m","TD2m")

                elif derived_var == "RF":
                    ds = idx.computeRF(paths_dict["PRCP"], paths_dict["SF"],"PRCP","SF")

                elif derived_var == "SD":
                    ds = idx.computeSD(paths_dict["SWE"], paths_dict["RSN"],"SWE","RSN")

                elif derived_var == "WS":
                    ds = idx.computeWS(paths_dict["UU"], paths_dict["VV"],"UU","VV")

                elif derived_var == "WD":
                    ds = idx.computeWD(paths_dict["UU"], paths_dict["VV"],"UU","VV")

                else:
                    continue

                
                # -------------------------------------------------
                # FORMAT AND SAVE
                # -------------------------------------------------
                ds = io.format_and_save(
                    ds=ds,
                    variable_raw=derived_var,
                    variable_final=derived_var,
                    frequency="hourly",
                    config=config,
                    out_path=out_path,
                    save_netcdf_func=save_netcdf,
                )
                
                ds.close()

    print("DERIVED VARS CALCULATION COMPLETED")