#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
from config import load_config
from cds import create_cds_client
from cds_download import ERA5Download
from process_masking import run_masking
from process_derived_vars import run_derived_vars
from process_fwi import run_fwi

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the ERA5-FWI-SN pipeline."
    )
    parser.add_argument(
        "--year-init", type=int, default=None,
        help="Initialization year (default: config.yaml fwi.year_init)"
    )
    parser.add_argument(
        "--year-start", type=int, default=None,
        help="First year to process (default: config.yaml fwi.year_start)"
    )
    parser.add_argument(
        "--year-end", type=int, default=None,
        help="Last year to process, inclusive (default: config.yaml fwi.year_end)"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    config = load_config()
    client = create_cds_client(
        config["cds"]["credentials"]
    )
    year_init = args.year_init or config["fwi"]["year_init"]
    year_start = args.year_start or config["fwi"]["year_start"]
    year_end = args.year_end or config["fwi"]["year_end"]
    years = range(year_start,year_end+1)
    
    # List of utc hours to keep for solar noon method
        # For Canada: from 15 to 22
    utc_list = config["utc_list"]

    # Run Pipeline
    ERA5Download(config, client).download_all(years=years)

    run_masking(config=config,years=years)

    run_derived_vars(config=config,years=years)
    
    # Run for all years
    # results is for last computed year only
    results = run_fwi(
        config=config,
        years=years, 
        year_init=year_init,
        utc_list=utc_list
        )

    print("FWI completed")

if __name__ == "__main__":
    main()