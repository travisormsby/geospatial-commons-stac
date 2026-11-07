import json
import subprocess
from contextlib import chdir
from pathlib import Path

import requests
import yaml


def init_catalog(catalog_root, **metadata):
    catalog_root.mkdir(parents=True, exist_ok=True)
    catalog_portolan_dir = catalog_root / ".portolan"
    if not catalog_portolan_dir.is_dir():
        init_args = [
            "portolan",
            "init",
            "--license",
            "other",
            "--license-url",
            "https://www.revisor.mn.gov/statutes/cite/13",
            catalog_root,
            "--auto",
        ]

        subprocess.run(init_args, check=True)

        metadata_file = catalog_portolan_dir / "metadata.yaml"
        update_metadata(metadata_file, **metadata)


def update_metadata(metadata_file, **metadata):

    generated_metadata = yaml.safe_load(metadata_file.read_text())
    generated_metadata.update(metadata)

    metadata = {k: v for k, v in generated_metadata.items() if v}
    with open(metadata_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False, allow_unicode=True)


catalog_root = Path("mn_geospatial_commons")

catalog_title = "Minnesota Geospatial Commons STAC"
catalog_description = "Geospatial data for the state of Minnesota. This project is not affiliated with or endorsed by the Minnesota Geospatial Information Office (MnGeo), Minnesota IT Services (MNIT), or any other office of the State of Minnesota."
contact_info = {"name": "Travis Ormsby", "email": "travis.ormsby@gmail.com"}
data_provider = {
    "name": "Minnesota Geospatial Information Office (MnGeo)",
    "roles": ["producer", "licensor"],
    "url": "https://gis.data.mn.gov/",
}
processor_provider = {
    "name": "Travis Ormsby",
    "roles": ["processor", "host"],
    "url": "https://github.com/travisormsby/geospatial-commons-stac",
}

providers = [data_provider, processor_provider]

catalog_processing_notes = (
    "Extracted from public ArcGIS FeatureServer layers with the Portolan CLI."
)

catalog_metadata = {
    "title": catalog_title,
    "description": catalog_description,
    "contact": contact_info,
    "providers": providers,
    "processing_notes": catalog_processing_notes,
}


init_catalog(catalog_root, **catalog_metadata)

# Mapping of service URLs to ArcGIS Online item pages for MN Geospatial Commons services
with open("service_info.json") as f:
    service_info = json.load(f)

# Folder to scrape
services_dir = "https://enterprise.gisdata.mn.gov/aghost/rest/services"
# folder = "us_mn_state_sos"
folder = ""
folder_dir = catalog_root / folder
init_catalog(folder_dir)

add_args = [
    "portolan",
    "add",
    "--portolan-dir",
    catalog_root,
    "--force",
    folder_dir,
]
subprocess.run(add_args, check=True)

# Extract feature service data to parquet and add to parent catalog
services = requests.get(f"{services_dir}/{folder}?f=pjson").json()["services"]
for service in services:
    if service["type"] == "FeatureServer":
        url = f"{services_dir}/{service['name']}/FeatureServer"
        license_url = service_info[url]["details"]
        output_dir = catalog_root / service["name"].lower()
        output_dir.mkdir(parents=True, exist_ok=True)

        extract_args = [
            "portolan",
            "extract",
            "arcgis",
            url,
            output_dir,
            "--license",
            "other",
            "--license-url",
            license_url,
            "--auto",
        ]
        subprocess.run(extract_args, check=True)

        title = service_info[url]["title"]
        description = service_info[url]["description"]
        update_metadata(
            output_dir / ".portolan" / "metadata.yaml",
            title=title,
            description=description,
            contact=contact_info,
            providers=providers,
        )

        for child in output_dir.iterdir():
            try:
                update_metadata(
                    child / ".portolan" / "metadata.yaml",
                    contact=contact_info,
                    providers=providers,
                )
            except FileNotFoundError, NotADirectoryError:
                print(f"{child} is not a data directory, skipping metadata update.")

        add_args = [
            "portolan",
            "add",
            "--portolan-dir",
            output_dir.parent,
            "--force",
            "--thumbnails",
            output_dir,
        ]
        subprocess.run(add_args, check=True)

        with chdir(catalog_root):
            readme_args = ["portolan", "readme"]
            subprocess.run(readme_args, check=True)

            check_args = ["portolan", "check", "--fix"]
            subprocess.run(check_args, check=True)
