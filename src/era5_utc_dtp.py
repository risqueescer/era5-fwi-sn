import numpy as np
import xarray as xr


class UTCDailyTotalPrecip:
    """
    Compute specific UTC daily total precipitation used in FWI preprocessing.
    """

    # -----------------------------------------------------
    # ALIGN TIME
    # -----------------------------------------------------
    def _align(self, ds1, ds2):
        if len(ds1.time) > len(ds2.time):
            ds1 = ds1.isel(time=slice(0, len(ds2.time)))
        elif len(ds2.time) > len(ds1.time):
            ds2 = ds2.isel(time=slice(0, len(ds1.time)))
        return ds1, ds2

    # -----------------------------------------------------
    # DTP CORE COMPUTATION
    # -----------------------------------------------------
    
    def compute_dtp(self, prcp, utc, last_24h_day):
        import pandas as pd
    
        h1 = list(range(0, utc + 1))
        h2 = list(range(utc + 1, 24))
    
        # Unique calendar days present, in chronological order  avoids the
        # day-of-month collision when `prcp` spans multiple months.
        unique_days = prcp.time.dt.floor("D").to_index().unique()[:last_24h_day]
    
        out = []
    
        for date in unique_days:
            day = prcp.sel(time=prcp.time.dt.floor("D") == date)
            tmp1 = day.sel(time=day.time.dt.hour.isin(h1)).sum(dim="time", min_count=1)
            
            prev_date = date - pd.Timedelta(days=1)
            
            if prev_date in unique_days:
                prev = prcp.sel(time=prcp.time.dt.floor("D") == prev_date)
                tmp2 = prev.sel(time=prev.time.dt.hour.isin(h2)).sum(dim="time", min_count=1)
            else:
                tmp2 = xr.where(tmp1.notnull(), 0, np.nan)
    
            out.append(tmp1 + tmp2)
    
        dtp_da = xr.concat(out, dim="time")
        dtp_da["time"] = unique_days
        return dtp_da

    # -----------------------------------------------------
    # MULTI-UTC WRAPPER 
    # -----------------------------------------------------
    def build_dtp_multi(self, prcp_ds, utc_list, last_24h_day):

        prcp = prcp_ds["PRCP"]

        dtp_vars = {}

        for utc in utc_list:

            dtp = self.compute_dtp(prcp, utc, last_24h_day)

            dtp_vars[f"DTP_{utc}"] = dtp

        ds = xr.Dataset(dtp_vars)
        

        ds.attrs["description"] = "Daily total precipitation for multiple UTC cutoffs"

        return ds