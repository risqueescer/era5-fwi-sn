# CDSdownload.py
from utils import get_last_date, save_netcdf # generics utils
from paths import DataPaths
from calendar import monthrange
import numpy as np
import xarray as xr


class ERA5Download:
    """
    Download hourly ERA5 single-level variables from CDS.

    Example
    -------
    downloader = ERA5Download(
        output_dir="./data",
        area=[88, 200, 38, 320]
    )

    ERA5download.download_all()
    """

    VARIABLES = {
        "t2m": "2m_temperature",
        "d2m": "2m_dewpoint_temperature",
        "tp": "total_precipitation",
        "sd": "snow_depth",
        "rsn": "snow_density",
        "u10": "10m_u_component_of_wind",
        "v10": "10m_v_component_of_wind",
    }

    HOURS = [
        f"{h:02}:00"
        for h in range(24)
    ]

    def __init__(
        self,
        config,
        cds_client=None,
    ):
        paths = DataPaths(config) 
        self.output_dir = paths.paths["cds_era5_dir"] 
        
        
        self.cds_client = cds_client

        self.area = config["era5_download"]["area"]
    
        self.day_lag = config["era5_download"]["day_lag"]
    
        self.variables = config["era5_download"]["variables"]
        
        

    # ============================================================
    # PATH UTILITIES
    # ============================================================

    def build_output_path(
        self,
        variable,
        year,
        month,
    ):
        month_str = f"{month:02d}"

        directory = (
            self.output_dir
            / variable
            / "ll"
            / "nc4"
            / str(year)
            / month_str
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"era5_{variable}_ll_{year}{month_str}_1h.nc4"
        )

        return directory / filename

    # ============================================================
    # DATASET CHECKING
    # ============================================================
    def merge_expver(self, ds):
        """Merge ERA5 expver streams (typically 1 and 5)."""
    
        if "expver" not in ds.dims:
            return ds
    
        expvers = ds.expver.values
        
        if len(expvers) == 1:
            return ds.isel(expver=0, drop=True)
        
        ds = (
            ds.sel(expver=expvers[0])
            .combine_first(ds.sel(expver=expvers[1])))
    
        return ds
    
    def format_dataset(self, ds):

        if "valid_time" in ds:
            ds = ds.rename(
                {"valid_time": "time"}
            )

        if "number" in ds:
            ds = ds.drop_vars("number")

        ds = self.merge_expver(ds)
        
        return ds

    def expected_last_time(
        self,
        year,
        month,
    ):
        n_days = monthrange(year, month)[1]

        return np.datetime64(
            f"{year}-{month:02d}-{n_days:02d}"
            "T23:00:00"
        )

    def latest_available_time(self):
        last_date = get_last_date(6)
        
        return np.datetime64(
            f"{last_date.year}-"
            f"{last_date.month:02d}-"
            f"{last_date.day:02d}"
            "T23:00:00"
        )

    def file_is_complete(
        self,
        filepath,
        year,
        month,
    ):
        if not filepath.exists():
            return False

        try:

            ds = xr.open_dataset(filepath)

            if "time" not in ds.dims:
                ds.close()
                return False

            last_time = ds.time[-1].values

            ds.close()

            expected = self.expected_last_time(
                year,
                month,
            )

            latest_available = (
                self.latest_available_time()
            )

            if last_time == expected:
                return True

            if last_time == latest_available:
                return True

            return False

        except Exception:
            return False

    # ============================================================
    # DOWNLOAD
    # ============================================================

    def build_request(
        self,
        variable,
        year,
        month,
    ):
        n_days = monthrange(year, month)[1]

        days = [
            f"{d:02d}"
            for d in range(1, n_days + 1)
        ]

        return {
            "product_type": "reanalysis",
            "format": "netcdf",
            "variable": self.VARIABLES[variable],
            "year": str(year),
            "month": f"{month:02d}",
            "day": days,
            "time": self.HOURS,
            "area": self.area,
        }

    def download_month(
        self,
        variable,
        year,
        month,
        overwrite=False,
    ):

        filepath = self.build_output_path(
            variable,
            year,
            month,
        )
        #print (filepath)
        if filepath.exists() and not overwrite:

            if self.file_is_complete(filepath, year, month):
                print(f"✓ Complete file exists: {filepath.name}")
                return filepath
    
            print(f"Removing incomplete file: {filepath.name}")
            filepath.unlink()
            
        print(
            f"Downloading "
            f"{variable} "
            f"{year}-{month:02d}"
        )

        request = self.build_request(
            variable,
            year,
            month,
        )

        self.cds_client.retrieve(
            "reanalysis-era5-single-levels",
            request,
            str(filepath),
        )

        self.postprocess_file(filepath)

        return filepath

    # ============================================================
    # POST-PROCESSING
    # ============================================================

    def postprocess_file(
        self,
        filepath,
    ):

        if not filepath.exists():
            return

        ds = xr.open_dataset(filepath)

        ds = self.format_dataset(ds)

        tmp_path = filepath.with_suffix(
            ".tmp.nc"
        )
        
        # save netcdf with utils function
        save_netcdf(ds, tmp_path)

        ds.close()

        filepath.unlink()
        tmp_path.rename(filepath)

    # ============================================================
    # BULK DOWNLOAD
    # ============================================================

    def download_all(self,years):
        last_date = get_last_date(self.day_lag)

        for variable in self.variables:

            for year in years:

                if year == last_date.year:
                    months = range(
                        1,
                        last_date.month + 1,
                    )
                else:
                    months = range(1, 13)

                for month in months:

                    try:

                        self.download_month(
                            variable,
                            year,
                            month,
                        )

                    except Exception as exc:

                        print(
                            f"Failed:"
                            f" {variable} "
                            f"{year}-{month:02d}"
                        )

                        print(exc)