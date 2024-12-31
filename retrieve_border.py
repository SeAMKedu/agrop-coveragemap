import argparse
import geopandas as gpd
import json
import logging
import osm2geojson

from decimal import Decimal
from functools import partial
from urllib.request import urlopen

OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# Query to get the administrative boundary of Etelä-Pohjanmaa
OVERPASS_QUERY = '''
[out:json];
( area["ISO3166-1"="FI"][admin_level=2]; )->.a;
rel["name"="Etelä-Pohjanmaa"][admin_level=4](area.a);
out geom;
'''

READ_CHUNK_SIZE = 4096

def fetch_region_border(query):
    logger.info("Fetching region border from Overpass API")
 
    response = b""
    query = query.encode("utf-8")
    try:
        with urlopen(OVERPASS_URL, query) as f:
            f_read = partial(f.read, READ_CHUNK_SIZE)
            for data in iter(f_read, b""):
                response += data
    except Exception as exc:
        raise exc

    if f.code == 200:
            if isinstance(data, bytes):
                response = response.decode("utf-8")
            
            data_parsed: dict = json.loads(response, parse_float=Decimal)
            return data_parsed
    else:
        raise Exception()


def convert_osm2geojson(osm_data):
    """ Convert OSM data to GeoJSON format """  
    logger.info("Converting OSM data to GeoJSON format")
  
    geojson = osm2geojson.json2geojson(osm_data)

    return geojson

def simplify_geojson(geojson, tolerance=0.001):
    logger.info("Simplifying GeoJSON data")

    gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs="EPSG:4326")
    gdf_simplified = gdf.copy()
    gdf_simplified['geometry'] = gdf_simplified['geometry'].simplify(tolerance=tolerance, preserve_topology=True)

    return json.loads(gdf_simplified.to_json())

def parseCommandLineArguments():
    parser = argparse.ArgumentParser(description='Station list updater')
    
    parser.add_argument("-v", "--verbose", action='count', default=0, help="Verbose output, twice for debug messages")
    parser.add_argument("-ns", "--no-simplification", action='store_true', help="Skip simplification")
    parser.add_argument("-t", "--tolerance", type=float, default=0.001, help="Tolerance used for simplification")
    parser.add_argument("-o", "--output", type=str, help="Overwrite previously fetched data, use - for stdout", required=True)
    
    parser.add_argument("query", type=str, nargs='?', default=OVERPASS_QUERY, help='Overpass query to use')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parseCommandLineArguments()
    
    if args.verbose >= 2:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    logger = logging.getLogger("retrieve_border.py")

    query_result = fetch_region_border(args.query)

    geojson = convert_osm2geojson(query_result)

    if not args.no_simplification:
        geojson = simplify_geojson(geojson)

    if args.output == "-":
        print(json.dumps(geojson))
    else:
        logger.info(f"Writing output to {args.output}") 
        with open(args.output, 'w') as file:
            json.dump(geojson, file)
