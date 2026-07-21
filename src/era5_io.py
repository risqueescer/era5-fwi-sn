import numpy as np

class ERA5IO:
    """
    ERA5-specific I/O and formatting utilities.
    """

    # -----------------------------------------------------
    # FORMAT DATASET
    # -----------------------------------------------------
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
    
    def format_ds(self, ds):
        """
        Standardize ERA5 dataset structure if needed.
        """
        # Merge expver if dimension is present
        ds = self.merge_expver(ds)
        
        # Format longitudes
        ds = ds.assign_coords(
            lon=((ds.lon + 180) % 360) - 180
        )
        
        return ds

    # -----------------------------------------------------
    # MASK APPLICATION 
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
        
        from datetime import datetime
        
        attrs_dict = {
            'lat':
                {'units': 'degrees_north',
                 'standard_name': 'latitude',
                 'long_name': 'latitude',
                 'stored_direction': 'decreasing',
                 'axis': 'Y'},
            'lon':
                {'units': 'degrees_east',
                 'standard_name': 'longitude',
                 'long_name': 'longitude',
                 'axis': 'X'},
            'FWI':
                {"long_name":"Fire Weather Index",
                 
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'DMC':
                {"long_name":"Duff Moisture Code",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'DC':
                {"long_name":"Drought Code",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'ISI':
                {"long_name":"Initial Spread Index",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'BUI':
                {"long_name":"Buildup Index",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'FFMC':
                {"long_name":"Fine Fuel Moisture Code",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'DSR':
                {"long_name":"Daily Severity Rating",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'DSRc':
                {"long_name":"Cumulative Daily Severity Rating",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'DCf':
                {"long_name":"End-of-season Drought Code",
                 "comment": (
                    "Computed using the solar noon method with fire season onset method "
                    "'%s' and initialization year '%s'."
                    % (config["fwi"]["onset_method"], config["fwi"]["year_init"])
                    ),
                 },
            'Onset':
                {"long_name":"Fire season onset day of year",
                 "units":"1",
                 "comment": (
                    "Day of year (1-365/366) indicating the start of the fire season. "
                    "Determined using onset method '%s'."
                    % config["fwi"]["onset_method"]
                    ),
                 },
            'WinterOnset':
                {"long_name":"Fire season end day of year",
                 "units":"1",
                 "comment": (
                    "Day of year (1-365/366) indicating the start of the winter. "
                    "Determined using onset method '%s'."
                    % config["fwi"]["onset_method"]
                    ),
                 },
            'WinterRain':
                {"long_name":"Winter accumulated precipitation",
                 "units":"mm"},
            'FSL':
                {"long_name":"Fire Season Length",
                 "units":"days",
                 "comment": (
                    "Determined using onset method '%s'."
                    % config["fwi"]["onset_method"]
                    ),
                 },
            'T2m':
                {"long_name":"2 metre air temperature",
                 "units":"degC",
                 "standard_name":"air_temperature"},
            'TD2m':
                {"long_name":"2 metre dew point temperature",
                 "units":"degC",
                 "standard_name":"dew_point_temperature"},
            'PRCP':
                {"long_name":"Accumulated precipitation",
                 "units":"mm"},
            'SWE':
                {"long_name":"Snow water equivalent",
                 "units":"m",
                 "standard_name":"snow_water_equivalent"},
            'UU':
                {"long_name":"Eastward wind component",
                 "units":"m s-1",
                 "standard_name":"eastward_wind"},
            'VV':
                {"long_name":"Northward wind component",
                 "units":"m s-1",
                 "standard_name":"northward_wind"},
            'RSN':
                {"long_name":"Snow density",
                 "units":"kg m-3",
                 "standard_name":"snow_density"},
            'SD':
                {"long_name":"Snow Depth",
                 "units":"m",
                 "standard_name":"snow_depth"},
            'WS':
                {"long_name":"Wind Speed",
                 "units":"km h-1",
                 "standard_name":"wind_speed"},
            'WD':
                {"long_name":"Wind direction",
                 "units":"degrees",
                 "standard_name": "wind_from_direction",
                 "valid_range": [0.0, 360.0],
                 "comment":(
                    "Meteorological wind direction: direction from which the wind blows, "
                    "clockwise from north."
                )},
            'RH':
                {"long_name":"Relative humidity",
                 "units":"%",
                 "standard_name":"relative_humidity"},
            'DTP':
                {"long_name":"24h accumulated precipitation",
                 "units":"mm"},
                 
            }
        # Update data variable name and attributes
        ds = ds.rename_vars({variable_raw: variable_final})
        ds[variable_final].attrs = attrs_dict.get(variable_final, {})
        
        # Update dims attributes
        ds.lat.attrs  = attrs_dict['lat']
        ds.lon.attrs  = attrs_dict['lon']
        
        # Update dataset attributes
        ds.attrs = {
            "conventions":"",
            'organisation_name':config["organisation"],
            "data_source": config["data_source"],
            "output_frequency": frequency,
            'creation_date': str(datetime.today()),
            'horizontal_resolution': "%s degrees"%(config["grid_resolution"]),
            'spatial_ref':'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',   
        }
    
        save_netcdf_func(ds, out_path)
    
        return ds