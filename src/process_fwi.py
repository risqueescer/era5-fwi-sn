import numpy as np
import xarray as xr
from pathlib import Path

from utils import last_complete_day, save_netcdf, is_current_year
from era5_io import ERA5IO
from paths import DataPaths
from era5_utc_dtp import UTCDailyTotalPrecip
from era5_solar_noon import SolarNoonValue
from fwi_fire_season_indices import FireSeasonIndices
from fwi_core import compute_fwi


def daily_max_t2m(hourly_t2m_ds):
    daily_tmax = hourly_t2m_ds["T2m"].resample(time='1D').max()
    return (daily_tmax)

def daily_mean_snow_depth(sd_files,swe_files):
    # provide snow value (sd or swe) in meters
    from pathlib import Path
    # Calculate daily mean snow depth or estimate it 
    missing = [f for f in sd_files if not Path(f).exists()]
    
    if len(missing) == 0:
        sd_ds = xr.open_mfdataset(sd_files, combine="by_coords")
        # convert from cm to meter
        sd_ds["SD"] = sd_ds["SD"] 
    else:
        print("No SD data, using SWE instead")
        SNOW_DENSITY = 100  
        
        swe_ds = xr.open_mfdataset(swe_files, combine="by_coords")
        swe = swe_ds["SWE"] 
        sd = swe * (1000 / SNOW_DENSITY)
        sd_ds = sd.to_dataset(name="SD")
    
    # Calculate daily mean snow depth
    sd_dmean = sd_ds["SD"].resample(time='1D').mean()
    return (sd_dmean)

def snow_condition(sd_dmean):
    # Only keep snow for Jan + Feb
    sd_JF = sd_dmean.sel(time=sd_dmean.time.dt.month.isin([1,2])) 
    # mask sd_JF where snow < 0.10 m (condition for Onset calculation)
    sd_cond_JF = xr.where(sd_JF >= 0.10, 1, 0).where(~np.isnan(sd_JF))
    return (sd_cond_JF)

    
def run_fwi(config,years, year_init,utc_list):

    print("'process_fwi' started...")
    
    # ----------------------------------
    # CONFIGURATION
    # ----------------------------------
    io = ERA5IO()
    paths = DataPaths()
    
    day_lag = config["era5_download"]["day_lag"]
    snow_th = config["fwi"]["snow_threshold"]
    # ----------------------------------
    # LOOP YEARS
    # ----------------------------------
    for year in years:
        print ("*YEAR '%s'*"%(year))
        
        fwi_check_path = paths.fwi_sn_daily('FWI', year)
        if fwi_check_path.exists() and not is_current_year(year,day_lag):
            print(f"[SKIP] FWI outputs already exist for {year}")
            continue
        
        # ----------------------------------
        # INPUTS
        # ----------------------------------
        # Inputs for FWI calculations (values at solar noon)
        t2m_files = [
            paths.masked_hourly("T2m", year, m)
            for m in range(1, 13)
        ]
        rh_files = [
            paths.masked_hourly("RH", year, m)
            for m in range(1, 13)
        ]
        ws_files = [
            paths.masked_hourly("WS", year, m)
            for m in range(1, 13)
        ]
        prcp_files = [
            paths.masked_hourly("PRCP", year, m)
            for m in range(1, 13)
        ]
        
        swe_files = [
            paths.masked_hourly("SWE", year, m)
            for m in range(1, 13)
        ]
        
        sd_files = [
            paths.masked_hourly("SD", year, m)
            for m in range(1, 13)
        ]
        
        dcf_py_path = paths.fwi_sn_daily('DCf', year-1)
        
        print("Reading Input Variable Files...") 
        h_t2m_ds = xr.open_mfdataset(
            t2m_files,
            combine="by_coords"
        )
        h_rh_ds = xr.open_mfdataset(
            rh_files,
            combine="by_coords"
        )
        h_ws_ds = xr.open_mfdataset(
            ws_files,
            combine="by_coords"
        )
        h_prcp_ds = xr.open_mfdataset(
            prcp_files,
            combine="by_coords"
        )
        
        # Last DC value of previous year
        dcf_py_available = False
        if dcf_py_path.exists():
            dcf_py_ds = xr.open_dataset(dcf_py_path)
            dcf_py_available = True
            
        # WinterOnset of Previous Year
        wonset_py_path = paths.fire_season_indices('WinterOnset', year - 1)
        wonset_py_available = False
        if wonset_py_path.exists():
            wonset_py_ds = xr.open_dataset(wonset_py_path)
            wonset_py = wonset_py_ds["WinterOnset"].values
            wonset_py_available = True
            
        # Extract daily total precipitation - DTP - at specific UTC hours
        # First get the number of complete days (24hrs) in file
        last_24h_day = last_complete_day(h_prcp_ds)
        utc_dtp_ds = UTCDailyTotalPrecip().build_dtp_multi(h_prcp_ds,utc_list,last_24h_day)
    
        # Coordinates for daily output datasets
        lats = h_t2m_ds.lat.values
        lons = h_t2m_ds.lon.values

        dates = [
            d.to_pydatetime()
            for d in h_t2m_ds.time.dt.floor("D").to_index().unique()
        ]

        print("STEP 1: Fire Season Indices")
        print("--> Preparing Inputs...") 
        # Inputs for Fire Season Indices calculation
        # 1. Daily maximum temperature
        t2m_dmax_da = daily_max_t2m(h_t2m_ds)
        
        # 2. Daily mean snow depth
        sd_dmean_da = daily_mean_snow_depth(sd_files,swe_files)
        sd_cond_JF = snow_condition(sd_dmean_da)
        nb_days_sd_cond = len(sd_cond_JF.time)
        sd_cond_percent_da = (
            sd_cond_JF
            .sum(dim="time")
            * 100.0
            / nb_days_sd_cond
        )
        # 3. Previous year daily total precipitation
        prcp_py_available = False
        prcp_files_py = [
            paths.masked_hourly("PRCP", year-1, m)
            for m in range(1, 13)
        ]
        
        missing_prcp_py = [f for f in prcp_files_py if not Path(f).exists()]
        if len(missing_prcp_py) == 0:
            h_prcp_ds_py = xr.open_mfdataset(
                prcp_files_py,
                combine="by_coords"
            )
            last_24h_day_py = last_complete_day(h_prcp_ds_py)
            utc_dtp_ds_py = UTCDailyTotalPrecip().build_dtp_multi(h_prcp_ds_py,utc_list,last_24h_day_py)
            prcp_py_available = True
        # ----------------------------------
        # DIMENSIONS
        # ----------------------------------

        ny, nx = len(lats), len(lons)
    
        onset = np.full((ny, nx), np.nan)
    
        winter_onset = np.full((ny, nx), np.nan)
    
        fsl = np.full((ny, nx), np.nan)
    
        winter_rain = np.full((ny, nx), np.nan)
    
        # ----------------------------------
        # FIRE SEASON INDICES
        # ----------------------------------
        # First transform xarrays into numpy arrays
        t2m_dmax = t2m_dmax_da.values
        sd_dmean = sd_dmean_da.values
        dtp_cy = utc_dtp_ds["DTP_17"].values
        if prcp_py_available:
            dtp_py = utc_dtp_ds_py["DTP_17"].values
        sd_cond_percent = sd_cond_percent_da.values
        
        print("--> Computing Fire Season Indices...") 
        for i in range(ny):
            for j in range(nx):
                # Prepare for Fire Season Indices calculations
                indices = FireSeasonIndices.compute_all(
    
                    t2m_ij=t2m_dmax[:,i, j],
    
                    sd_ij=sd_dmean[:,i, j],
    
                    dtp_cy_ij=dtp_cy[:, i, j],
    
                    dtp_py_ij=dtp_py[:, i, j] if prcp_py_available else None,
                    
                    winter_onset_py_ij=wonset_py[i, j] if wonset_py_available else np.nan, 
                    
                    sd_cond_percent_ij=sd_cond_percent[i, j],
    
                    onset_method="TS",
    
                    snow_th=snow_th,
    
                    temp_th_onset=12.0, # Temperature threshold for Onset
                    
                    temp_th_wonset=5.0, # Temperature threshold for WinterOnset
                )
    
                onset[i, j] = indices["Onset"]
    
                winter_onset[i, j] = indices["WinterOnset"]
    
                fsl[i, j] = indices["FSL"]
    
                winter_rain[i, j] = indices["WinterRain"]
        
        # Construct xarray dataset
        onset_ds = xr.Dataset(coords = {'lat': (['lat'], lats),'lon': (['lon'], lons)})
        onset_ds["Onset"] = (['lat', 'lon'],  onset)
        
        winter_onset_ds = xr.Dataset(coords = {'lat': (['lat'], lats),'lon': (['lon'], lons)})
        winter_onset_ds["WinterOnset"] = (['lat', 'lon'],  winter_onset)
        
        fsl_ds = xr.Dataset(coords = {'lat': (['lat'], lats),'lon': (['lon'], lons)})
        fsl_ds["FSL"] = (['lat', 'lon'],  fsl)
        
        winter_rain_ds = xr.Dataset(coords = {'lat': (['lat'], lats),'lon': (['lon'], lons)})
        winter_rain_ds["WinterRain"] = (['lat', 'lon'],  winter_rain)
        
        # Format and save Fire season indices
        onset_path = paths.fire_season_indices('Onset', year)
        winter_onset_path = paths.fire_season_indices('WinterOnset', year)
        winter_rain_path = paths.fire_season_indices('WinterRain', year)
        fsl_path = paths.fire_season_indices('FSL', year)
        
        onset_path.parent.mkdir(parents=True, exist_ok=True)
        winter_onset_path.parent.mkdir(parents=True, exist_ok=True)
        winter_rain_path.parent.mkdir(parents=True, exist_ok=True)
        fsl_path.parent.mkdir(parents=True, exist_ok=True)
        
        onset_ds = io.format_and_save(
            ds=onset_ds,
            variable_raw="Onset",
            variable_final="Onset",
            frequency="yearly",
            config=config,
            out_path=onset_path,
            save_netcdf_func=save_netcdf,
        )
        winter_onset_ds = io.format_and_save(
            ds=winter_onset_ds,
            variable_raw="WinterOnset",
            variable_final="WinterOnset",
            frequency="yearly",
            config=config,
            out_path=winter_onset_path,
            save_netcdf_func=save_netcdf,
        )
        winter_rain_ds = io.format_and_save(
            ds=winter_rain_ds,
            variable_raw="WinterRain",
            variable_final="WinterRain",
            frequency="yearly",
            config=config,
            out_path=winter_rain_path,
            save_netcdf_func=save_netcdf,
        )
        fsl_ds = io.format_and_save(
            ds=fsl_ds,
            variable_raw="FSL",
            variable_final="FSL",
            frequency="yearly",
            config=config,
            out_path=fsl_path,
            save_netcdf_func=save_netcdf,
        )
        
    
        print("STEP 2: FWI")
        
        # Read input values at solar noon
        print("--> Interpoling Input Values at Solar Noon...") 
        solar_noon_ds = SolarNoonValue().interpolate(
            h_t2m_ds,
            h_rh_ds,
            h_ws_ds,
            utc_dtp_ds,
            lats,
            lons,
            dates
        )
        
        t2m_da = solar_noon_ds["T2m"]
        rh_da = solar_noon_ds["RH"]
        ws_da = solar_noon_ds["WS"]
        dtp_da = solar_noon_ds["DTP"]
    
        print("--> Computing FWI...") 
        fwi_ds, ffmc_ds, dmc_ds, dc_ds, isi_ds, bui_ds, dsr_ds, dsrc_ds, dcf_ds = compute_fwi(
    
            t2m=t2m_da.values,
    
            rh=rh_da.values,
    
            ws=ws_da.values,
    
            dtp=dtp_da.values,
    
            onset=onset,
    
            wonset=winter_onset,
            
            lats=lats,
            
            lons=lons,
            
            dates=dates,
            
            year=year,
            
            year_init=year_init,
            
            dcf_py = dcf_py_ds["DCf"].values if dcf_py_available else None,
            
            wr=winter_rain,
    
            method="sn_dc",
            
            # Fraction values
            # Following Hanes and Wotton (2024)
            bF = 0.5,
            aF = 1.0
        )
        
        # -------------------------------------------------
        # FORMAT AND SAVE
        # -------------------------------------------------
        print("Format and Save Files...") 
        
        # Set Output paths
        # FWI components
        fwi_path = paths.fwi_sn_daily('FWI', year)
        ffmc_path = paths.fwi_sn_daily('FFMC', year)
        dmc_path = paths.fwi_sn_daily('DMC', year)
        dc_path = paths.fwi_sn_daily('DC', year)
        isi_path = paths.fwi_sn_daily('ISI', year)
        bui_path = paths.fwi_sn_daily('BUI', year)
        dsr_path = paths.fwi_sn_daily('DSR', year)
        
        # Fire Season Indices
        dsrc_path = paths.fire_season_indices('DSRc', year)
        dcf_path = paths.fire_season_indices('DCf', year)
        
        
        # Out dir fwi & fire_season_indices:
        fwi_path.parent.mkdir(parents=True, exist_ok=True)
        ffmc_path.parent.mkdir(parents=True, exist_ok=True)
        dmc_path.parent.mkdir(parents=True, exist_ok=True)
        dc_path.parent.mkdir(parents=True, exist_ok=True)
        isi_path.parent.mkdir(parents=True, exist_ok=True)
        bui_path.parent.mkdir(parents=True, exist_ok=True)
        dsr_path.parent.mkdir(parents=True, exist_ok=True)
        # Fire Season Indices
        dsrc_path.parent.mkdir(parents=True, exist_ok=True)
        dcf_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save datasets to NetCDF files
        # FWI components
        fwi_ds = io.format_and_save(
            ds=fwi_ds,
            variable_raw="FWI",
            variable_final="FWI",
            frequency="daily",
            config=config,
            out_path=fwi_path,
            save_netcdf_func=save_netcdf,
        )
        
        ffmc_ds = io.format_and_save(
            ds=ffmc_ds,
            variable_raw="FFMC",
            variable_final="FFMC",
            frequency="daily",
            config=config,
            out_path=ffmc_path,
            save_netcdf_func=save_netcdf,
        )
        dmc_ds = io.format_and_save(
            ds=dmc_ds,
            variable_raw="DMC",
            variable_final="DMC",
            frequency="daily",
            config=config,
            out_path=dmc_path,
            save_netcdf_func=save_netcdf,
        )
        dc_ds = io.format_and_save(
            ds=dc_ds,
            variable_raw="DC",
            variable_final="DC",
            frequency="daily",
            config=config,
            out_path=dc_path,
            save_netcdf_func=save_netcdf,
        )
        isi_ds = io.format_and_save(
            ds=isi_ds,
            variable_raw="ISI",
            variable_final="ISI",
            frequency="daily",
            config=config,
            out_path=isi_path,
            save_netcdf_func=save_netcdf,
        )
        bui_ds = io.format_and_save(
            ds=bui_ds,
            variable_raw="BUI",
            variable_final="BUI",
            frequency="daily",
            config=config,
            out_path=bui_path,
            save_netcdf_func=save_netcdf,
        )
        dsr_ds = io.format_and_save(
            ds=dsr_ds,
            variable_raw="DSR",
            variable_final="DSR",
            frequency="daily",
            config=config,
            out_path=dsr_path,
            save_netcdf_func=save_netcdf,
        )
        dsrc_ds = io.format_and_save(
            ds=dsrc_ds,
            variable_raw="DSRc",
            variable_final="DSRc",
            frequency="yearly",
            config=config,
            out_path=dsrc_path,
            save_netcdf_func=save_netcdf,
        )
        dcf_ds = io.format_and_save(
            ds=dcf_ds,
            variable_raw="DCf",
            variable_final="DCf",
            frequency="yearly",
            config=config,
            out_path=dcf_path,
            save_netcdf_func=save_netcdf,
        )

        # -------------------------------------------------
        # CLOSE OPEN DATASETS (avoid file-handle buildup over long runs)
        # -------------------------------------------------
        h_t2m_ds.close()
        h_rh_ds.close()
        h_ws_ds.close()
        h_prcp_ds.close()

        if dcf_py_available:
            dcf_py_ds.close()

        if wonset_py_available:
            wonset_py_ds.close()

        if prcp_py_available:
            h_prcp_ds_py.close()
    
    return {year:{
        "FWI": fwi_ds,
        "FFMC": ffmc_ds,
        "DMC": dmc_ds,
        "DC": dc_ds,
        "ISI": isi_ds,
        "BUI": bui_ds,
        "DSR": dsr_ds,
        "DSRc": dsrc_ds,
        "DCf": dcf_ds,
        "Onset": onset_ds,
        "WinterOnset": winter_onset_ds,
        "FSL": fsl_ds,
        "WinterRain": winter_rain_ds,
        }
    }
