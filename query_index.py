import duckdb

with duckdb.connect() as conn:
    conn.execute("INSTALL spatial; LOAD spatial;")
    rel = conn.sql("""
        SELECT href
        FROM 'https://stac.travisormsby.com/mn_geocommons_stac/catalog-index/collections.parquet' 
        WHERE ST_Within(
            ST_GeomFromText('POLYGON ((-97 46, -96 46, -96 47, -97 46))'),
            geometry
        )
    """)
    rel.show()
