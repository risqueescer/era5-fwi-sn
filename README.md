# era5-fwi-sn
Python pipeline to compute a daily gridded Fire Weather Index (FWI) dataset for Canada from ERA5 reanalysis data, using solar-noon-based local time correction.

## Project Structure
```text
era5-fwi-sn/

├── README.md                       # Project documentation
├── LICENSE  
├── environment.yml                 # Conda environment specification
│
├── config/                         # Configuration files
│   └── config.yaml
│
├── src/                            # Core application source code
│   ├── main.py
│   ├── cds_download.py
│   ├── process_masking.py
│   ├── process_derived_vars.py
│   ├── process_fwi.py
│   ├── config.py
│   ├── paths.py
│   ├── utils.py
│   ├── era5_io.py
│   ├── cds.py
│   ├── era5_derived_vars.py
│   ├── era5_utc_dtp.py
│   ├── era5_solar_noon.py
│   ├── fwi_fire_season_indices.py
│   └── fwi_core.py
│
├── shp/                             # Shapefile used to mask ERA5 to the Canadian domain
│   └── gpr_limites_canada_wgs84.shp
│
│├── output/                           # Output data directories
│   ├── cds_era5/
│   ├── masked/
│   ├── derived_vars/
│   ├── fwi_inputs/
│   ├── fire_season_indices/
│   └── fwi-sn/
│
└── logs/
```
## Features
- Downloads hourly ERA5 single-level variables (2 m temperature, dewpoint, precipitation, snow depth/density, wind components) from the Copernicus Climate Data Store (CDS).
- Masks the data to the Canadian domain using a shapefile and `regionmask`.
- Computes derived hourly variables: relative humidity, effective rainfall, snow depth, wind speed and direction.
- Interpolates inputs to local solar noon for each grid cell using `astral`, so FWI is computed at physically consistent local times across the whole domain.
- Computes the full Canadian FWI System (FFMC, DMC, DC, ISI, BUI, FWI), daily severity rating (DSR/DSRc), and fire-season phenology indices (Onset, Winter Onset, Fire Season Length, Winter Rain), including DC overwintering between years.
- Pipeline is resumable: years/months already fully processed are skipped on re-run, except the current year (per the CDS ~6-day data lag), which is always refreshed.

## Prerequisites
- [Miniconda or Anaconda](https://docs.conda.io/en/latest/miniconda.html) (the pipeline uses Python 3.9, pinned via `environment.yml`).
- A free [Copernicus Climate Data Store (CDS)](https://cds.climate.copernicus.eu) account, needed to download ERA5 data.

### Setting up CDS API access
1. Create an account at https://cds.climate.copernicus.eu and accept the ERA5 dataset license.
2. From your CDS profile page, copy your API URL and key.
3. Create `~/.cdsapirc` with the following content:
   ```yaml
   url: <your CDS API URL>
   key: <your CDS API key>
   ```
   This path matches `cds.credentials` in `config/config.yaml` by default; change that value if you'd rather store the file elsewhere.

## Installation
1. Clone the repository:
   ```bash
   git clone git@github.com:risqueescer/era5-fwi-sn.git
   cd era5-fwi-sn
   ```
2. Create and activate the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate era5-fwi-sn
   ```

## How to run

### Reproduce the paper
Runs the full year range defined in `config/config.yaml` (`fwi.year_init` to `fwi.year_end`):
```bash
python src/main.py
```

### Single year / partial range
Override the year range from the command line without editing the config file:
```bash
python src/main.py --year-init 1950 --year-start 1950 --year-end 1950
```
Note: FWI relies on the Drought Code (DC) carried over from the previous year ("overwintering"). If the previous year hasn't already been processed, the pipeline falls back to the standard DC spin-up values for that run rather than failing — useful for quick tests, but for scientifically valid output over a partial range, process years sequentially from `fwi.year_init` onward at least once.

### Custom configuration
All region, method, and threshold choices are controlled by `config/config.yaml` — there is no separate `--config` flag; edit the file directly, e.g.:
```yaml
spatial_domain: Can
fwi:
  onset_method: TS      # T | TS | TS0 | ToS
  snow_threshold: 0.01
  temperature_threshold: 5.0
```
Then run as usual:
```bash
python src/main.py
```

## License
Distributed under the MIT License. See the `LICENSE` file in the root directory for more details.

## How to cite
Code: [Zenodo DOI — add after tagging the release used in the paper]

Dataset: see **Data Availability** below.

## Contact

Clémence Benoît - benoit.clemence@uqam.ca
Philippe Gachon - gachon.philippe@uqam.ca

Repository: https://github.com/risqueescer/era5-fwi-sn
Clone: `git@github.com:risqueescer/era5-fwi-sn.git`

## Data Availability
The full time series (1950 to the most recent complete year available) of the daily FWI System components and other fire-season-related indices is available as the ERA5-FWI-SN dataset in both NetCDF and GeoTIFF formats via the Borealis platform: https://doi.org/10.5683/SP3/4B18XZ (Benoit et al., 2025).

Dataset DOI: [10.5683/SP3/4B18XZ](https://doi.org/10.5683/SP3/4B18XZ)

Dataset Reference: Benoit, C., Durand, J., Gachon, P., Boulanger, Y., and Boucher, J.: ERA5-FWI-SN dataset (V1), TS30 [data set], https://doi.org/10.5683/SP3/4B18XZ, 2025.