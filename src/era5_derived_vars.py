import numpy as np
import xarray as xr


class DerivedVars:
    """
    Compute ERA5 derived hourly variables:
    RH, RF, SD, WS, WD
    """

    # ---------------------------------------------------------
    # RELATIVE HUMIDITY
    # ---------------------------------------------------------
    def computeRH(self, t2m_path, d2m_path, t2m_var="T2m", d2m_var="TD2m"):

        t2m_ds = xr.open_dataset(t2m_path)
        d2m_ds = xr.open_dataset(d2m_path)

        # -------------------------------------------------
        # ALIGN TIME DIMENSIONS (important fix kept from original)
        # -------------------------------------------------
        len_t2m = len(t2m_ds.time)
        len_d2m = len(d2m_ds.time)

        if len_t2m > len_d2m:
            t2m_ds = t2m_ds.isel(time=slice(0, len_d2m))
        elif len_d2m > len_t2m:
            d2m_ds = d2m_ds.isel(time=slice(0, len_t2m))

        # -------------------------------------------------
        # CONVERT DEGC TO KELVIN
        # -------------------------------------------------
        t2m = t2m_ds[t2m_var] + 273.15
        d2m = d2m_ds[d2m_var] + 273.15

        # -------------------------------------------------
        # RH FORMULA (your original physics)
        # -------------------------------------------------
        rh = (
            (6.11 * np.exp(5417.7530 * ((1 / 273.16) - (1 / d2m))))
            /
            (6.11 * np.exp(5417.7530 * ((1 / 273.16) - (1 / t2m))))
        ) * 100

        rh = xr.where(rh > 100, 100, rh)

        ds = rh.to_dataset(name="RH")
        ds["RH"].attrs = {
            "units": "%",
            "long_name": "Relative humidity"
        }
        t2m_ds.close()
        d2m_ds.close()

        return ds

    # ---------------------------------------------------------
    # SNOW DEPTH (physical conversion)
    # ---------------------------------------------------------
    def computeSD(self, swe_path, rsn_path, swe_var="SWE", rsn_var="RSN"):
        # SWE need to be in meters (of snow water equivalent)
        # Return SD in meters
        swe_ds = xr.open_dataset(swe_path)
        rsn_ds = xr.open_dataset(rsn_path)

        # align time
        len_swe = len(swe_ds.time)
        len_rsn = len(rsn_ds.time)

        if len_swe > len_rsn:
            swe_ds = swe_ds.isel(time=slice(0, len_rsn))
        elif len_rsn > len_swe:
            rsn_ds = rsn_ds.isel(time=slice(0, len_swe))

        swe = swe_ds[swe_var] #/ 1000.0   # mm → m
        rsn = rsn_ds[rsn_var]

        water_density = 1000.0

        sd = swe * water_density / rsn #* 100.0  # m → cm

        ds = sd.to_dataset(name="SD")
        ds["SD"].attrs = {
            "units": "m",
            "long_name": "Estimated snow depth"
        }

        swe_ds.close()
        rsn_ds.close()

        return ds

    # ---------------------------------------------------------
    # WIND SPEED
    # ---------------------------------------------------------
    def computeWS(self, uu_path, vv_path, uu_var = "UU", vv_var = "VV"):

        uu_ds = xr.open_dataset(uu_path)
        vv_ds = xr.open_dataset(vv_path)

        uu = uu_ds[uu_var]
        vv = vv_ds[vv_var]

        ws = np.sqrt(uu**2 + vv**2)

        # m/s → km/h (your original conversion)
        ws = ws / 1000.0 * 3600.0

        ds = ws.to_dataset(name="WS")
        ds["WS"].attrs = {
            "units": "km h-1",
            "long_name": "Wind speed"
        }

        uu_ds.close()
        vv_ds.close()

        return ds

    # ---------------------------------------------------------
    # WIND DIRECTION
    # ---------------------------------------------------------
    def computeWD(self, uu_path, vv_path, uu_var = "UU", vv_var = "VV"):

        uu_ds = xr.open_dataset(uu_path)
        vv_ds = xr.open_dataset(vv_path)

        uu = uu_ds[uu_var]
        vv = vv_ds[vv_var]

        abs_wind = np.sqrt(uu**2 + vv**2)

        wd = np.arctan2(vv / abs_wind, uu / abs_wind)
        wd = np.degrees(wd)

        wd = 90 - (wd + 180)

        wd = wd.where(wd >= 0, wd + 360)

        ds = wd.to_dataset(name="WD")
        ds["WD"].attrs = {
            "units": "degrees",
            "long_name": "Wind direction",
            "standard_name": "wind_from_direction",
        }
        
        uu_ds.close()
        vv_ds.close()

        return ds