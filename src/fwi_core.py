import math
import numpy as np
import pandas as pd
import xarray as xr

# =========================================================
# CORE FWI PHYSICS
# =========================================================
class FWICLASS:
    def __init__(self, temp, rhum, wind, prcp):
        self.t = temp
        self.h = rhum
        self.w = wind
        self.p = prcp

    # ---------------- FFMC ----------------
    def FFMCcalc(self, ffmc0):
        mo = (147.2 * (101.0 - ffmc0)) / (59.5 + ffmc0)

        if self.p > 0.5:
            rf = self.p - 0.5
            if mo > 150.0:
                mo = (mo + 42.5 * rf * np.exp(-100.0 / (251.0 - mo)) *
                      (1.0 - np.exp(-6.93 / rf))) + (.0015 * (mo - 150.0) ** 2) * np.sqrt(rf)
            else:
                mo = mo + 42.5 * rf * np.exp(-100.0 / (251.0 - mo)) * (1.0 - np.exp(-6.93 / rf))

        mo = min(mo, 250.0)

        ed = (.942 * (self.h ** .679) +
              11.0 * np.exp((self.h - 100.0) / 10.0) +
              0.18 * (21.1 - self.t) * (1.0 - np.exp(-0.115 * self.h)))

        if mo < ed:
            ew = (.618 * (self.h ** .753) +
                  10.0 * np.exp((self.h - 100.0) / 10.0) +
                  0.18 * (21.1 - self.t) * (1.0 - np.exp(-0.115 * self.h)))

            if mo <= ew:
                kl = (.424 * (1.0 - ((100.0 - self.h) / 100.0) ** 1.7) +
                      .0694 * np.sqrt(self.w) * (1.0 - ((100.0 - self.h) / 100.0) ** 8))
                kw = kl * (.581 * np.exp(.0365 * self.t))
                m = ew - (ew - mo) / 10.0 ** kw
            else:
                m = mo
        else:
            kl = (.424 * (1.0 - (self.h / 100.0) ** 1.7) +
                  .0694 * math.sqrt(self.w) * (1.0 - (self.h / 100.0) ** 8))
            kw = kl * (.581 * np.exp(.0365 * self.t))
            m = ed + (mo - ed) / 10.0 ** kw

        ffmc = (59.5 * (250.0 - m)) / (147.2 + m)
        return max(0.0, min(ffmc, 101.0))

    # ---------------- DMC ----------------
    def DMCcalc(self, dmc0, mth):
        el = [6.5,7.5,9.0,12.8,13.9,13.9,12.4,10.9,9.4,8.0,7.0,6.0]

        t = max(self.t, -1.1)

        rk = 1.894 * (t + 1.1) * (100.0 - self.h) * (el[mth - 1] * 0.0001)

        if self.p <= 1.5:
            pr = dmc0
        else:
            ra = self.p
            rw = 0.92 * ra - 1.27
            wmi = 20.0 + 280.0 / math.exp(0.023 * dmc0)

            if dmc0 <= 33.0:
                b = 100.0 / (0.5 + 0.3 * dmc0)
            elif dmc0 <= 65.0:
                b = 14.0 - 1.3 * math.log(dmc0)
            else:
                b = 6.2 * math.log(dmc0) - 17.2

            wmr = wmi + (1000 * rw) / (48.77 + b * rw)
            pr = 43.43 * (5.6348 - math.log(wmr - 20.0))

        return max(0.0, pr + rk)

    # ---------------- DC ----------------
    def DCcalc(self, dc0, mth):
        fl = [-1.6,-1.6,-1.6,0.9,3.8,5.8,6.4,5.0,2.4,0.4,-1.6,-1.6]

        t = max(self.t, -2.8)
        pe = (0.36 * (t + 2.8) + fl[mth - 1]) / 2

        if self.p > 2.8:
            rw = 0.83 * self.p - 1.27
            smi = 800.0 * math.exp(-dc0 / 400.0)
            dr = dc0 - 400.0 * math.log(1.0 + ((3.937 * rw) / smi))
            dr = max(0.0, dr)
            dc = dr + pe
        else:
            dc = dc0 + pe

        return max(0.0, dc)

    # ---------------- ISI ----------------
    def ISIcalc(self, ffmc):
        mo = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
        ff = 19.115 * math.exp(-0.1386 * mo) * (1.0 + (mo ** 5.31) / 49300000.0)
        return ff * math.exp(0.05039 * self.w)

    # ---------------- BUI ----------------
    def BUIcalc(self, dmc, dc):
        if dmc == 0 and dc == 0:
            return 0.0

        bui = (0.8 * dc * dmc) / (dmc + 0.4 * dc)

        if bui < dmc:
            p = (dmc - bui) / dmc
            cc = 0.92 + (0.0114 * dmc) ** 1.7
            bui = dmc - cc * p

        return max(0.0, bui)

    # ---------------- FWI ----------------
    def FWIcalc(self, isi, bui):
        if bui <= 80:
            bb = 0.1 * isi * (0.626 * bui ** 0.809 + 2.0)
        else:
            bb = 0.1 * isi * (1000.0 / (25.0 + 108.64 / math.exp(0.023 * bui)))

        if bb <= 1.0:
            return bb
        return math.exp(2.72 * (0.434 * math.log(bb)) ** 0.647)

    # ---------------- FULL STEP ----------------
    def step(self, ffmc0, dmc0, dc0, month):
        ffmc = self.FFMCcalc(ffmc0)
        dmc  = self.DMCcalc(dmc0, month)
        dc   = self.DCcalc(dc0, month)

        isi  = self.ISIcalc(ffmc)
        bui  = self.BUIcalc(dmc, dc)
        fwi  = self.FWIcalc(isi, bui)

        return ffmc, dmc, dc, isi, bui, fwi


# =========================================================
# 1) FIRE SEASON INDICES INITIAL VALUES
# =========================================================

def fwi_init_values(dcf_py_ij, wr_ij, bF, aF,
                          year, year_init, ffmc_init=85, dmc_init=6, dc_init=15,
                          method="sn_dc"):
    
    def overwintering():
        qf=800.0 * math.exp(-dcf_py_ij/400.0)
        qs=aF*qf+bF*(3.94*(wr_ij))
        dc=400*math.log(800/qs) # DC start-up value
        return max(dc_init, dc)
    
    def init_dc():
        if year == year_init:
            return dc_init

        if method == "sn_dc":
            if np.isnan(dcf_py_ij) or dcf_py_ij < 50:
                return dc_init
            else:
                return overwintering()

        if method == "sn_wr":
            if wr_ij < 200:
                return overwintering()
            else:
                return dc_init

        return dc_init
    
    return ffmc_init, dmc_init, init_dc()


# =========================================================
# 2) CORE FWI SEASON LOOP
# =========================================================

def compute_fwi(t2m, rh, ws, dtp,
                        onset, 
                        wonset,
                        lats,
                        lons,
                        dates,
                        year, 
                        year_init=1950,
                        dcf_py=None, 
                        wr=None,
                        method="sn_dc",
                        bF = 0.5,
                        aF = 1.0):
    

    # Dimensions and empty np.arrays to store results
    nt, ny, nx = len(dates), len(lats), len(lons)

    fwi = np.full((nt, ny, nx), np.nan)
    ffmc = np.full((nt, ny, nx), np.nan)
    dmc  = np.full((nt, ny, nx), np.nan)
    dc   = np.full((nt, ny, nx), np.nan)
    isi   = np.full((nt, ny, nx), np.nan)
    bui   = np.full((nt, ny, nx), np.nan)
    
    dcf   = np.full((ny, nx), np.nan)

    for i in range(ny):
        for j in range(nx):

            if np.isnan(onset[i, j]):
                continue

            start = int(onset[i, j]) - 1 # -1 to get the date index 
            stop = int(wonset[i, j]) - 2 if not np.isnan(wonset[i, j]) else nt - 1

            ffmc0, dmc0, dc0 = fwi_init_values(
                dcf_py[i,j] if dcf_py is not None else np.nan,
                wr[i,j] if wr is not None else np.nan,
                bF,
                aF,
                year,
                year_init,
                method=method
            )

            for t in range(start, stop + 1):

                temp = t2m[t, i, j]
                rhum = rh[t, i, j]
                wind = ws[t, i, j]
                prcp = dtp[t, i, j]

                fwisys = FWICLASS(temp, rhum, wind, prcp)
                
                if t == start:
                    ffmc0, dmc0, dc0 = ffmc0, dmc0, dc0
                    
                else:
                    ffmc0 = ffmc[t-1, i, j]
                    dmc0  = dmc[t-1, i, j]
                    dc0   = dc[t-1, i, j]

                ffmc[t,i,j], dmc[t,i,j], dc[t,i,j], isi[t,i,j], bui[t,i,j], fwi[t,i,j] = \
                    fwisys.step(ffmc0, dmc0, dc0, pd.Timestamp(dates[t]).month)
                
                if t == stop:
                    dcf[i,j] = dc[t,i,j]
                else:
                    pass
    
    # Final steps: calculate final indices and generate xarray datasets               
    # Calculate final indices DSR, DSRc and DCf
    # Daily severity rating (DSR)
    # DSR = 0.0272 * FWI^1.77 + cumulated SR
    dsr = 0.0272 * np.power(fwi, 1.77)
    dsr_ds = xr.Dataset(coords = {'time': (['time'], dates),
                                  'lat': (['lat'], lats),'lon': (['lon'], lons)})
    dsr_ds["DSR"] = (['time','lat', 'lon'],  dsr)
    
    # Cumulated severity rating (DSRc)
    dsrc = dsr_ds['DSR'].sum(dim='time',skipna=True,min_count=1)
    dsrc_ds = dsrc.to_dataset(name='DSRc')
    
    # Final Drought Code Value (DCf)
    dcf_ds = xr.Dataset(coords = {'lat': (['lat'], lats),'lon': (['lon'], lons)})
    dcf_ds["DCf"] = (['lat', 'lon'],  dcf)
    

    # Create xarray dataset from numpy array for all indices
    # FWI
    fwi_ds = xr.Dataset(coords = {'time': (['time'], dates),
                                  'lat': (['lat'], lats),'lon': (['lon'], lons)})
    fwi_ds["FWI"] = (['time','lat', 'lon'],  fwi)
    
    # FFMC
    ffmc_ds = xr.Dataset(coords = {'time': (['time'], dates),
                                  'lat': (['lat'], lats),'lon': (['lon'], lons)})
    ffmc_ds["FFMC"] = (['time','lat', 'lon'],  ffmc)
    
    # DC
    dc_ds = xr.Dataset(coords = {'time': (['time'], dates),
                                  'lat': (['lat'], lats),'lon': (['lon'], lons)})
    dc_ds["DC"] = (['time','lat', 'lon'],  dc)
    
    # DMC
    dmc_ds = xr.Dataset(coords = {'time': (['time'], dates),
                                  'lat': (['lat'], lats),'lon': (['lon'], lons)})
    dmc_ds["DMC"] = (['time','lat', 'lon'],  dmc)
    
    # ISI
    isi_ds = xr.Dataset(coords = {'time': (['time'], dates),
                                  'lat': (['lat'], lats),'lon': (['lon'], lons)})
    isi_ds["ISI"] = (['time','lat', 'lon'],  isi)
    
    # BUI
    bui_ds = xr.Dataset(coords = {'time': (['time'], dates),
                                  'lat': (['lat'], lats),'lon': (['lon'], lons)})
    bui_ds["BUI"] = (['time','lat', 'lon'],  bui)
    
    
    #return dataset individually
    return (fwi_ds,
            ffmc_ds, 
            dmc_ds, 
            dc_ds, 
            isi_ds, 
            bui_ds, 
            dsr_ds,
            dsrc_ds,
            dcf_ds)