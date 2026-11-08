The goal of this project is a proof-of-concept for converting ArcGIS feature services in the [Minnesota Geospatial Commons](https://gis.data.mn.gov/) to parquet files accessible through a SpatioTemporal Asset Catalog (STAC).

This project is not affiliated with or endorsed by the State of Minnesota, Minnesota IT Services (MNIT), or the Minnesota Geospatial Information Office (MnGEO).

Using the [Portolan CLI](https://cli.portolan-sdi.org/), these services can be extracted from ArcGIS, sorted by Hilbert order, and published as GeoParquet in cloud object storage. A STAC browser can use the catalog.json file at the root of the collection to allow browsing the data sets. The STAC can also be queried directly with DuckDB.

## Setup:

1. Ensure that `uv` is installed
1. Install portolan: `uv tool install portolan-cli`
1. Install dependencies: `uv sync`
1. Generate the service information: `uv run python get-service-info.py`
1. Configure cloud bucket variables:
    - `PORTOLAN_REMOTE`, example: `s3://<bucket>/<folder>`
    - `PORTOLAN_S3_ENDPOINT`, for S3-compatible storage, example: `https://<account_id>.r2.cloudflarestorage.com`
    - `PORTOLAN_S3_USE_SSL=true`
    - `AWS_ACCESS_KEY_ID`
    - `AWS_SECRET_ACCESS_KEY`

    export these variables or put them in an `.env` file in the root of the STAC directory (not the root of the repo)

1. Change the metadata at the top of `extract.py` to your own name and contact info.

## Use:

Run the `extract.py` script with any number of space-deliminted service URLs. For example:

```bash
uv run python extract.py https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dot/biota_wild_rice/FeatureServer https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mde/bdry_school_attendance_areas/FeatureServer
```

The script will attempt to extract the data for each layer of the service as GeoParquet and add it to the STAC.

## Example

I am hosting a subset of data I extracted from the Minnesota Geospatial Commons using this script. You can see the example in the [moreGeo STAC browser](https://browser.moregeo.it/external/pub-fd7f8d9b83e64eefadd68ec6ea715112.r2.dev/mn_geocommons_stac/catalog.json)

The data are hosted on a free-tier R2 bucket in CloudFlare, so please don't hammer it with requests or I'll have to take it down. But it should serve to explore what it looks like to have these GeoParquet files organized in a STAC.

## Limitations

- Hosted feature layers do not appear to work as input. At least those published to MnGeo's ArcGIS Enterprise deployment. It's not clear to me whether this is a problem with the script, with Portolan, or with the way the services are published. 

- The script is designed for data in published to MnGeo's ArcGIS Enterprise deployment. To work with other ArcGIS Online or ArcGIS Enterprise organizations,`get-service-info.py` would need a different way to identify relevant content items and the metadata at the top of `extract.py` would need to be updated.




