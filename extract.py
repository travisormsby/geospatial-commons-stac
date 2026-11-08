import json
import subprocess
from contextlib import chdir
from pathlib import Path
from urllib.parse import urlsplit

import requests
import yaml

SOURCE_URL = "https://enterprise.gisdata.mn.gov/aghost/rest/services"
CATALOG_DIR = Path("./mn_geocommons_stac")
CATALOG_ID = "mn-geospatial-data"
CATALOG_TITLE = "Minnesota Geospatial Data"
CATALOG_DESCRIPTION = "Geospatial data for the state of Minnesota. This project is not affiliated with or endorsed by the Minnesota Geospatial Information Office (MnGeo), Minnesota IT Services (MNIT), or any other office of the State of Minnesota."
CATALOG_LICENSE_URL = "https://www.revisor.mn.gov/statutes/cite/13"
CATALOG_CONTACT = {"name": "Travis Ormsby", "email": "travis.ormsby@gmail.com"}
CATALOG_PROVIDERS = [
    {
        "name": "Minnesota Geospatial Information Office (MnGeo)",
        "roles": ["producer", "licensor"],
        "url": "https://gis.data.mn.gov/",
    },
    {
        "name": "Travis Ormsby",
        "roles": ["processor", "host"],
        "url": "https://github.com/travisormsby/geospatial-commons-stac",
    },
]
CATALOG_PROCESSING_NOTES = (
    "Extracted from public ArcGIS FeatureServer layers with the Portolan CLI."
)


def run_portolan(args: list[str], cwd: Path | None = None):
    """Run a portolan CLI command and stream output."""
    cmd = ["portolan", *args]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def update_metadata(metadata_file, **kwargs):

    metadata = yaml.safe_load(metadata_file.read_text())
    metadata.update(kwargs)

    metadata = {k: v for k, v in metadata.items() if v}
    with open(metadata_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False, allow_unicode=True)


def add_service(url):
    url_path = Path(urlsplit(url).path)
    rel_extraction_path = Path(*url_path.parts[4:-1])

    title = service_info[url]["title"]
    description = service_info[url]["description"]
    details_url = service_info[url]["details"]

    run_portolan(
        [
            "extract",
            "arcgis",
            url,
            str(rel_extraction_path),
            "--license",
            "other",
            "--license-url",
            details_url,
            "--auto",
        ],
        cwd=CATALOG_DIR,
    )

    run_portolan(
        [
            "add",
            "--force",
            "--thumbnails",
            str(rel_extraction_path),
        ],
        cwd=CATALOG_DIR,
    )

    for metadata_file in (CATALOG_DIR / rel_extraction_path).rglob("metadata.yaml"):
        update_metadata(metadata_file, contact=CATALOG_CONTACT)

    update_metadata(
        CATALOG_DIR / rel_extraction_path / ".portolan/metadata.yaml",
        title=title,
        description=description,
    )


if not (CATALOG_DIR / "catalog.json").exists():
    run_portolan(
        [
            "init",
            str(CATALOG_DIR),
            "--id",
            CATALOG_ID,
            "--license",
            "other",
            "--license-url",
            CATALOG_LICENSE_URL,
            "--auto",
        ]
    )

update_metadata(
    CATALOG_DIR / ".portolan" / "metadata.yaml",
    title=CATALOG_TITLE,
    description=CATALOG_DESCRIPTION,
    providers=CATALOG_PROVIDERS,
    contact=CATALOG_CONTACT,
    processing_notes=CATALOG_PROCESSING_NOTES,
)


with open("service_info.json") as f:
    service_info = json.load(f)

url = "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_health/bdry_svi_index_2020/FeatureServer"

add_service(url)


run_portolan(["readme"], cwd=CATALOG_DIR)
run_portolan(["check", "--fix"], cwd=CATALOG_DIR)
