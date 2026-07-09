# paths.py
from pathlib import Path
from config import load_config

class DataPaths:

    def __init__(self, config=None):
        self.cfg = config or load_config()
        
        # Project root
        project_root = Path(__file__).resolve().parent.parent

        # Resolve configured root_dir
        root_dir_cfg = self.cfg["project"]["root_dir"]

        if Path(root_dir_cfg).is_absolute():
            self.root_dir = Path(root_dir_cfg)
        else:
            self.root_dir = project_root / root_dir_cfg

        # Resolve all paths
        self.paths = {
            key: self.root_dir / value
            for key, value in self.cfg["paths"].items()
        }
        
        self.organisation = self.cfg["organisation"]
        self.data_source = self.cfg["data_source"]
        self.domain = self.cfg["spatial_domain"]

    def shp_path(self):
        return (
            self.paths["shp_dir"]
            / self.cfg["shp_can_name"])
    
    def raw_hourly(self, variable, year, month):

        return (
            self.paths["cds_era5_dir"]
            / variable
            / "ll"
            / "nc4"
            / str(year)
            / f"{month:02d}"
            / f"era5_{variable}_ll_{year}{month:02d}_1h.nc4"
        )

    def masked_hourly(self, variable, year, month):

        return (
            self.paths["masked_dir"]
            / "era5"
            / variable
            / "hourly"
            / (
                f"{self.organisation}_"
                f"{self.data_source}_"
                f"{variable}_"
                f"{year}{month:02d}_"
                f"{self.domain}_0p25grid.nc"
            )
        )
    
    def fwi_sn_daily(self,variable,year):
        return (
            self.paths["fwi_sn_outputs_dir"]
            / variable
            / (
                f"{self.organisation}_"
                f"{self.data_source}_"
                f"{variable}-sn_"
                f"{year}_"
                f"{self.domain}_0p25grid.nc"
            )
        )
    def fire_season_indices(self,variable,year):
        return (
            self.paths["fire_season_indices_dir"]
            / variable
            / (
                f"{self.organisation}_"
                f"{self.data_source}_"
                f"{variable}_"
                f"{year}_"
                f"{self.domain}_0p25grid.nc"
            )
        )