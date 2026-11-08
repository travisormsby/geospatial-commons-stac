import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from sys import argv
from urllib.parse import urlsplit

import duckdb
import pystac
import yaml

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


@dataclass
class ServiceInfo:
    details: str
    title: str
    description: str


def run_portolan(args: list[str], cwd: Path | None = None) -> None:
    """Run a portolan CLI command and stream output."""
    cmd = ["portolan", *args]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def update_metadata(metadata_file: Path, **kwargs: str | dict[str, str]) -> None:
    """Update the default metadata with key/value pairs from **kwargs"""
    metadata = yaml.safe_load(metadata_file.read_text())
    metadata.update(kwargs)

    metadata = {k: v for k, v in metadata.items() if v}
    with open(metadata_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False, allow_unicode=True)


def add_service(url: str, service_info: ServiceInfo) -> None:
    """Given a service, add all its layers to the STAC as GeoParquet"""
    url_path_parts = [part.lower() for part in Path(urlsplit(url).path).parts]
    rel_extraction_path = Path(*url_path_parts[4:-1])

    # Extract the data from the service
    run_portolan(
        [
            "extract",
            "arcgis",
            url,
            str(rel_extraction_path),
            "--license",
            "other",
            "--license-url",
            service_info.details,
            "--auto",
        ],
        cwd=CATALOG_DIR,
    )

    # Nested directories cause problems with portolan versions.json
    # Delete them so they are generated fresh from the subsequent add
    for versions_file in (CATALOG_DIR / rel_extraction_path).rglob("versions.json"):
        versions_file.unlink()

    # Add the collection to the STAC
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
        title=service_info.title,
        description=service_info.description,
    )


def generate_index_parquet():
    """Create a queryable GeoParquet index to find data in the STAC"""
    root_catalog_path = CATALOG_DIR / "catalog.json"
    catalog = pystac.Catalog.from_file(root_catalog_path)

    conn = duckdb.connect()
    conn.execute("INSTALL spatial; LOAD spatial;")
    conn.execute(
        "CREATE TABLE collections (id VARCHAR, title VARCHAR, href VARCHAR, bbox GEOMETRY)"
    )

    for collection in catalog.get_all_collections():
        if collection.id == "catalog-index":
            continue
        xmin, ymin, xmax, ymax = collection.extent.spatial.bboxes[0]
        parquet_assets = [
            a for a in collection.assets.values() if a.href.endswith(".parquet")
        ]
        for asset in parquet_assets:
            data_href = (
                Path(asset.get_absolute_href())
                .relative_to(CATALOG_DIR.resolve())
                .as_posix()
            )
            insert_query = """
                INSERT INTO collections 
                VALUES ($id, $title, $href, ST_MakeEnvelope($xmin, $ymin, $xmax, $ymax))
            """
            insert_params = {
                "id": collection.id,
                "title": collection.title,
                "href": data_href,
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
            }
            conn.execute(insert_query, parameters=insert_params)

    index_dir = CATALOG_DIR / "catalog-index"
    index_dir.mkdir(exist_ok=True)

    output_query = "COPY collections to $outfile (FORMAT PARQUET)"
    output_params = {"outfile": str(index_dir / "collections.parquet")}
    conn.execute(output_query, parameters=output_params)

    run_portolan(["add", "--force", index_dir.name], cwd=CATALOG_DIR)


def main(urls):
    # Initialize root catalog
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
        service_info_dict = json.load(f)

    for url in urls:
        service_info = ServiceInfo(**service_info_dict[url])
        add_service(url, service_info)

    run_portolan(["readme"], cwd=CATALOG_DIR)
    run_portolan(["check", "--fix"], cwd=CATALOG_DIR)
    generate_index_parquet()
    run_portolan(["push"], cwd=CATALOG_DIR)


if __name__ == "__main__":
    urls = argv[1:]
    main(urls)
