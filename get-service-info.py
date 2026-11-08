import json

from arcgis.gis import GIS

gis = GIS()

gc_items = gis.content.search(
    query="owner:commons_etl_user OR owner:commons_user", max_items=2000
)

service_info = {
    item.url: {
        "details": item.homepage,
        "title": item.title,
        "description": item.description,
    }
    for item in gc_items
}

with open("service_info.json", "w", encoding="utf-8") as f:
    json.dump(service_info, f, indent=2)
