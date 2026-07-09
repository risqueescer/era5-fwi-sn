import numpy as np
import xarray as xr
from astral import Observer
from astral.sun import noon
from zoneinfo import ZoneInfo


class SolarNoonValue:
    """
    Interpolate hourly ERA5 variables to local solar noon.

    Parameters
    ----------
    h_t2m_ds : xarray.Dataset
        Hourly temperature dataset (variable: T2m).
    h_rh_ds : xarray.Dataset
        Hourly relative humidity dataset (variable: RH).
    h_ws_ds : xarray.Dataset
        Hourly wind speed dataset (variable: WS).
    utc_dtp_ds : xarray.Dataset
        Multi-variables dataset of the daily total precipitation (DTP)
        Each variable correspond to the DTP at specific UTC
        Example:
            utc_dtp_ds["DTP_15"],
            utc_dtp_ds["DTP_16"],
            utc_dtp_ds["DTP_17"],
            ...

    Returns
    -------
    dict
        {
            "T2m": Dataset,
            "RH": Dataset,
            "WS": Dataset,
            "DTP": Dataset
        }
    """

    def interpolate(
        self,
        h_t2m_ds,
        h_rh_ds,
        h_ws_ds,
        utc_dtp_ds,
        lats,
        lons,
        dates
    ):
        # Coordinates
        # lon: longitudes east of 179 degrees need to be negative
        ndays = len(dates)
        ny = len(lats)
        nx = len(lons)

        # -------------------------------------------------
        # Split hourly datasets by UTC hour
        # -------------------------------------------------

        t2m_hour = {
            h: h_t2m_ds["T2m"].sel(time=h_t2m_ds.time.dt.hour == h).values
            for h in range(24)
        }

        rh_hour = {
            h: h_rh_ds["RH"].sel(time=h_rh_ds.time.dt.hour == h).values
            for h in range(24)
        }

        ws_hour = {
            h: h_ws_ds["WS"].sel(time=h_ws_ds.time.dt.hour == h).values
            for h in range(24)
        }
        
        # dtp: get first all the utc (correspond to the variables of dataset)
        utc_list = [
            int(var[4:])
            for var in utc_dtp_ds.data_vars
            
        ]
        dtp_hour = {
            utc: utc_dtp_ds["DTP_%s"%(utc)].values
            for utc in utc_list
        }
        # -------------------------------------------------
        # Output arrays
        # -------------------------------------------------

        t2m = np.full((ndays, ny, nx), np.nan)
        rh = np.full((ndays, ny, nx), np.nan)
        ws = np.full((ndays, ny, nx), np.nan)
        dtp = np.full((ndays, ny, nx), np.nan)

        # -------------------------------------------------
        # Interpolation
        # -------------------------------------------------

        for i in range(ny):

            for j in range(nx):
                # Skip cells outside Canada
                if np.isnan(t2m_hour[0][0, i, j]):
                    continue
                
                #sun = daylight.Sunclock(lats[i], lons[j])
                observer = Observer(latitude=lats[i], longitude=lons[j])

                for d, date in enumerate(dates):

                    tsn = noon(
                        observer,
                        date=date,
                        tzinfo=ZoneInfo("UTC"),
                    )

                    h1 = tsn.hour
                    h2 = min(h1 + 1, 23)

                    w2 = tsn.minute / 60.0
                    w1 = 1.0 - w2
                    
                    t2m[d, i, j] = (
                        w1 * t2m_hour[h1][d, i, j]
                        + w2 * t2m_hour[h2][d, i, j]
                    )

                    rh[d, i, j] = (
                        w1 * rh_hour[h1][d, i, j]
                        + w2 * rh_hour[h2][d, i, j]
                    )

                    ws[d, i, j] = (
                        w1 * ws_hour[h1][d, i, j]
                        + w2 * ws_hour[h2][d, i, j]
                    )
                    
                    # for DTP, one variable for each utc
                    dtp[d, i, j] = (
                        w1 * dtp_hour[h1][d, i, j]
                        + w2 * dtp_hour[h2][d, i, j]
                    )

        coords = {
            "time": dates,
            "lat": lats,
            "lon": lons,
        }
        return xr.Dataset(
            data_vars={
                "T2m": (("time", "lat", "lon"), t2m),
                "RH": (("time", "lat", "lon"), rh),
                "WS": (("time", "lat", "lon"), ws),
                "DTP": (("time", "lat", "lon"), dtp),
            },
            coords=coords,
        )
