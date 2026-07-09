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
        year = int(prcp[0].time.dt.year)
        month = int(prcp[0].time.dt.month)
        #days =  pd.date_range(str(year)+'-'+str('{:02d}'.format(month))+'-01T'+str(utc), periods=last_24h_day, freq='D')
        days =  pd.date_range(str(year)+'-'+str('{:02d}'.format(month))+'-01T'+'00:00', periods=last_24h_day, freq='D')


        h1 = list(range(0, utc + 1))
        h2 = list(range(utc + 1, 24))

        out = []

        for d in range(1, last_24h_day + 1):

            day = prcp.sel(time=prcp.time.dt.day == d)
            prev = prcp.sel(time=prcp.time.dt.day == d - 1)

            tmp1 = day.sel(time=day.time.dt.hour.isin(h1)).sum(dim="time",min_count=1)

            if d == 1:
                #tmp2 = 0
                tmp2 = xr.where(tmp1.notnull(), 0, np.nan)
            else:
                tmp2 = prev.sel(time=prev.time.dt.hour.isin(h2)).sum(dim="time",min_count=1)

            out.append(tmp1 + tmp2)
        
        dtp_da = xr.concat(out, dim="time")
        dtp_da['time'] = days
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