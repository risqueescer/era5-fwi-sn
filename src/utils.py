'''
Functions that can be used with any dataset
'''
import os
import xarray as xr


# =========================================================
# TIME UTIL
# =========================================================
def get_last_date(day_lag):
    """
    Get the date before today with a specific number of days lag
    Default value is for ERA5 hourly data available on CDS (~6 days)
    """
    from datetime import date, timedelta
    return date.today() - timedelta(days=day_lag)

def is_current_year(year, day_lag):
    """
    True if `year` is still receiving ERA5 updates, i.e. matches the year
    of the latest available ERA5 data (today minus day_lag).
    """
    return year == get_last_date(day_lag).year

def last_complete_day(ds):
    days_count = len(ds.time.resample(time='1D').count())
    last_day_hrs_count = len(ds.sel(time=ds.time.dt.dayofyear == days_count).time)
    if last_day_hrs_count == 24:
        last_24h_day = days_count
    else:
        last_24h_day = days_count -1
    
    return last_24h_day
# =========================================================
# FILE OPS
# =========================================================
def remove_file(path):
    if os.path.exists(path):
        os.remove(path)

def save_netcdf(ds, path, complevel=5):
    encoding = {
        var: {"zlib": True, "complevel": complevel}
        for var in ds.data_vars
    }
    ds.to_netcdf(path, encoding=encoding, format="NETCDF4")
    
def create_dir(paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)

# =========================================================
# MASKING
# =========================================================
def create_mask(shp_path, reference_nc, lat_name="lat", lon_name="lon"):
    """
    Create a regionmask dataset from shapefile + NetCDF grid file.
    """

    import geopandas as gpd
    import regionmask

    shp = gpd.read_file(shp_path)

    if "feature_id" not in shp.columns:
        shp["feature_id"] = range(1, len(shp) + 1)

    ds = xr.open_dataset(reference_nc)

    # harmonize names if needed
    rename_dict = {}
    for d in ds.dims:
        if "lon" in d:
            rename_dict[d] = lon_name
        if "lat" in d:
            rename_dict[d] = lat_name

    ds = ds.rename(rename_dict)

    lon = ds[lon_name].values
    lat = ds[lat_name].values

    mask = regionmask.mask_geopandas(
        shp,
        lon,
        lat,
        lon_name=lon_name,
        lat_name=lat_name,
        numbers="feature_id"
    )

    return mask.to_dataset(name="region")

# =========================================================
# VALIDATION HELPERS
# =========================================================
def tb_error(code_execution_end=False):
    import traceback
    """Simple traceback printer (replacement for BASEFUN)."""
    tb = traceback.format_exc()
    print("ERROR TRACEBACK:\n", tb)

    if code_execution_end:
        print("Execution stopped due to error.")