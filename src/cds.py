from pathlib import Path
import yaml
import cdsapi


def create_cds_client(cdsapirc=None):
    """
    Create a CDS API client.

    If cdsapirc is None, use the default ~/.cdsapirc.
    """

    if cdsapirc is None:
        return cdsapi.Client()

    cdsapirc = Path(cdsapirc).expanduser()

    with open(cdsapirc) as f:
        credentials = yaml.safe_load(f)

    return cdsapi.Client(
        url=credentials["url"],
        key=credentials["key"],
    )