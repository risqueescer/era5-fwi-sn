import numpy as np

class ERA5IO:
    """
    ERA5-specific I/O and formatting utilities.
    """

    # -----------------------------------------------------
    # FORMAT DATASET (replacement of FORMAT.format_ds)
    # -----------------------------------------------------
    def format_ds(self, ds):
        """
        Standardize ERA5 dataset structure if needed.
        """
        # placeholder for your existing logic
        # (keep original behavior if you had cleaning steps)
        ds = ds.assign_coords(
            lon=((ds.lon + 180) % 360) - 180
        )
        return ds


    # -----------------------------------------------------
    # MASK APPLICATION (replacement of FORMAT.mask_nc)
    # -----------------------------------------------------
    def apply_mask(self, ds, mask):
        """
        Apply regionmask to ERA5 dataset.
        """
        # --- ensure consistent coordinate names
        if "latitude" in ds.coords:
            ds = ds.rename({"latitude": "lat", "longitude": "lon"})
    
        # --- align mask to dataset grid (important)
        mask_aligned = mask.interp_like(ds, method="nearest")
    
        # --- apply mask
        ds_masked = ds.where(~np.isnan(mask_aligned.region),drop=True)
        

        return ds_masked


    # -----------------------------------------------------
    # STANDARDIZATION FOR DATABASE
    # -----------------------------------------------------

    def format_and_save(self,
        ds,
        variable_raw,
        variable_final,
        frequency,
        config,
        out_path,
        save_netcdf_func,
        ):
        
        ds = ds.rename_vars({variable_raw: variable_final})
    
        ds.attrs.update({
            "frequency": frequency,
            "source": config["data_source"],
            "grid_resolution": config["grid_resolution"],
            "grid_type": config["grid_type"],
            "variable": variable_final,
        })
    
        save_netcdf_func(ds, out_path)
    
        return ds