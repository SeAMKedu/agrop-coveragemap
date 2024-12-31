import argparse
import configparser
import json
import logging
import os
import socket
import traceback
import geojson

from base64 import b64encode
from datetime import datetime
from geopy.distance import geodesic
from shapely.geometry import shape, Point
from shapely.ops import nearest_points


class NTRIPFetcher():


    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.USER_AGENT = "NTRIPBasestationMapper"
        self.VERSION = "1.0"
        self.logger = logging.getLogger(self.__class__.__name__)


    def fetch_ntrip_data(self):
        self.logger.info(f"Retrieving source table from {args.caster}")

        cachefile = self.config.get(args.caster, 'cachefile')
        caster_host = self.config.get(args.caster, 'caster')
        caster_port = self.config.getint(args.caster, 'port')
        username = self.config.get(args.caster, 'username')
        password = self.config.get(args.caster, 'password')
        useragent = f"{self.USER_AGENT}/{self.VERSION}"
        credentials = b64encode(f"{username}:{password}".encode()).decode()

        url = f"http://{caster_host}:{caster_port}/"
        self.logger.debug(f"Fetching data from {url}")
        
        request = f"""GET / HTTP/1.1\r
Host: {caster_host}:{caster_port}\r
User-Agent: {useragent}\r
Authorization: Basic {credentials}\r
Accept: */*\r
Connection: close\r
\r
"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((caster_host, caster_port))
            s.sendall(request.encode())

            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
        
            response_text = response.decode(errors='ignore')
            self.logger.info(f"Receiced {len(response)} bytes.")
            self.logger.debug(f"Response start: {response_text[:100]}")

            # strip response headers
            headers = ""
            header_end = response_text.find("\r\n\r\n")
            if header_end != -1:
                headers = response_text[:header_end]
                self.logger.debug(f"Headers:\n{headers}")
                body_start = header_end + 4 # skip empty lines
                response_text = response_text[body_start:]
                
            self.logger.debug(f"Response body start: {response_text[:100]}")

            if "SOURCETABLE 200 OK" in headers or "gnss/sourcetable" in headers:
                self.logger.debug(f"Caching source table to {cachefile}")
                sourcetable_content = response_text.splitlines()[1:] 
                with open(cachefile, 'w') as file:
                    file.write("\n".join(sourcetable_content))
            else:
                raise Exception(f"Failed to retrieve data from NTRIP caster. Response start: {response_text[:100]}")
        

class RegionalFilter():
    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if self.args.region is not None:
            with open(self.args.region, 'r') as file:
                region_geojson = geojson.load(file)

                # Assume the GeoJSON contains one feature with a multipolygon geometry
                if region_geojson['type'] == 'FeatureCollection':
                    for feature in region_geojson['features']:
                        if feature['geometry']['type'] == 'MultiPolygon':
                            self.polygon = shape(feature['geometry'])


    def filter_stations(self):
        filtered_stations = []
        
        # Read the station list from the cache file
        cachefile = self.config.get(args.caster, 'cachefile')
        with open(cachefile, "r") as cf:
            self.logger.info(f"Filtering source table from {cachefile}")
            
            for line in cf:
                if line.startswith("ENDSOURCETABLE"):
                    break

                if line.startswith("STR"):
                    station= line.split(";")

                    if station[9].strip() == 'none' or station[9].strip() == 'none':
                        continue

                    station_id = station[1].strip()
                    lat = float(station[9].strip())
                    lon = float(station[10].strip())
                    country = station[8].strip()

                    # Check if the station is in the specified region
                    if args.country is not None:
                        if args.country == country:
                            filtered_stations.append({"id": station_id, "lat": lat, "lon": lon, "caster": args.caster})
                        else:
                            pass # in wrong country
                    elif args.everything is not False:
                        filtered_stations.append({"id": station_id, "lat": lat, "lon": lon, "caster": args.caster})
                    elif self.is_station_in_or_near_region(lat, lon):
                        filtered_stations.append({"id": station_id, "lat": lat, "lon": lon, "caster": args.caster})
        
        self.logger.info(f"Filtered source table to {len(filtered_stations)} stations")

        return filtered_stations


    def is_station_in_or_near_region(self, lat, lon):
        point = Point(lon, lat)  # Note: GeoJSON uses [lon, lat], not [lat, lon]
        if self.polygon.contains(point):
            return True
        
        # Find the nearest point on the boundary of the MultiPolygon
        nearest = nearest_points(self.polygon, point)[0]
        distance = geodesic((lat, lon), (nearest.y, nearest.x)).km  # convert back to lat, lon

        if distance <= float(self.args.buffer):
            return True

        return False
    

class LocationSorter:


    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(self.__class__.__name__)


    def sort(self, stations):
        self.logger.info(f"Sorting stations by {self.args.sort}.")
        
        if self.args.sort == "id":
            return sorted(stations, key=self.sort_by_id)
        else:
            return sorted(stations, key=self.sort_global_nw_to_se)


    def sort_by_id(self, station):
        return station['id']


    def normalize_longitude(self, lon):
        return (lon + 180) % 360  # Convert to 0-360 range


    def sort_global_nw_to_se(self, location):
        lat = location['lat']
        lon = location['lon']
        # Normalize longitude to 0-360 for correct sorting around the date line
        norm_lon = self.normalize_longitude(lon)
        # Sort by latitude descending first, then by normalized longitude
        return (norm_lon, lat)


def parseCommandLineArguments():
    parser = argparse.ArgumentParser(description='Station list updater')
    
    parser.add_argument("-v", "--verbose", action='count', default=0, help="Verbose output, twice for debug messages")
    parser.add_argument("-f", "--fetch", action="store_true", help="Really fetch the data")
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite previously fetched data")
    parser.add_argument("-a", "--append", action="store_true", help="Append stations to existing list")
    parser.add_argument("-i", "--ini_file", type=str, default="ntrip.ini",  help='Path to the INI file, default is ntrip.ini')
    parser.add_argument("-b", "--buffer", type=int, default=20,  help='From how far outside the region are stations counted in')
    
    filter_area = parser.add_mutually_exclusive_group(required=True)
    filter_area.add_argument("-e", "--everything", action="store_true", help='Everything without filtering')
    filter_area.add_argument("-c", "--country", type=str, help='Three-letter country code for all basestations in country')
    filter_area.add_argument("-r", "--region", type=str, help='Geojson file containing region border')

    parser.add_argument("-s", "--sort", type=str, choices=['id', 'coordinates'], default="coordinates", help="How to sort the stations")

    parser.add_argument("caster", type=str, choices=['RTK2GO', 'CENTIPEDE', 'EMLID'], help="Which caster to poll stations from")
    parser.add_argument("output", type=str, help='Output JSON filename')
    
    return parser.parse_args()


def main(args, config):
    try:
        cachefile = config.get(args.caster, 'cachefile')
        
        if not os.path.exists(cachefile) and not args.fetch:
            raise Exception(f"Cache file {cachefile} does not exist. Need to retrieve source table list.")
        
        if args.fetch:
            if os.path.exists(cachefile):
                if not args.overwrite:
                    raise Exception("Data already exists in cache file. Use -o to overwrite.")
            
            if config.get(args.caster, "username") == None:
                raise Exception(f"Username not set in {args.ini_file}")

            NTRIPFetcher(args, config).fetch_ntrip_data()

        filter = RegionalFilter(args, config)
        stations = filter.filter_stations()

        data = {}
        if args.append and os.path.exists(args.output):
            with open(args.output, 'r') as f:
                data = json.load(f)
            data["stations"].extend(stations)
        else:
            data = {"stations": stations}

        sorter = LocationSorter(args)
        data["stations"] = sorter.sort(data["stations"])
        
        data["timestamp"] = datetime.now().isoformat()

        with open(args.output, "w") as f:
            logger.info(f"Saving filtered station list of {len(data['stations'])} stations to {args.output}")
            json.dump(data, f)

    except Exception as e:
        traceback.print_exc()


if __name__ == "__main__":
    args = parseCommandLineArguments()
    
    if args.verbose >= 2:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger("update_stations.py")

    logger.info(f"Reading config from {args.ini_file}")
    
    config = configparser.ConfigParser()
    config.read(args.ini_file)

    logger.debug(f"CLI arguments: {args}")

    main(args, config)
