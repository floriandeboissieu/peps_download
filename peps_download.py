#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import json
import time
import os
import os.path
import optparse
import sys
import zipfile
from datetime import date

###########################################################################


class OptionParser (optparse.OptionParser):

    def check_required(self, opt):
        option = self.get_option(opt)

        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)


###########################################################################
def check_rename(tmpfile, prod, prodsize, write_dir, extract):
    print(os.path.getsize(tmpfile), prodsize)
    if os.path.getsize(tmpfile) != prodsize:
        with open(tmpfile) as f_tmp:
            try:
                tmp_data = json.load(f_tmp)
                print("Result is a json file with content:")
                print(tmp_data)
                raise SysError('Error might come from a wrong password file.', -1)
                # sys.exit(-1)
            except ValueError:
                print("\ndownload was not complete, tmp file removed")
                os.remove(tmpfile)
                return

    zfile = "%s/%s.zip" % (write_dir, prod)
    os.rename(tmpfile, zfile)

    # Unzip file
    if extract and os.path.exists(zfile):
        try:
            with zipfile.ZipFile(zfile, 'r') as zf:
                safename = zf.namelist()[0].replace('/', '')
                zf.extractall(write_dir)
            safedir = os.path.join(write_dir, safename)
            if not os.path.isdir(safedir):
                raise Exception('Unzipped directory not found: ', zfile)

        except Exception as e:
            print(e)
            print('Could not unzip file: ' + zfile)
            os.remove(zfile)
            print('Zip file removed.')
            return

        else:
            print('product saved as : ' + safedir)
            os.remove(zfile)
            return

    print("product saved as : " + zfile)

###########################################################################
class SysError(Exception):
    def __init__(self, message, exit_code):
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)
    def __repr__(self):
        self.message

def parse_catalog(search_json_file, orbit, collection, clouds, sat):
    # Filter catalog result
    with open(search_json_file) as data_file:
        data = json.load(data_file)

    if 'ErrorCode' in data:
        raise SysError('file '+ search_json_file + ' contains an error:\n'+data['ErrorMessage'], -2)
        # sys.exit(-2)

    # Sort data
    download_dict = {}
    storage_dict = {}
    size_dict = {}
    if len(data["features"]) > 0:
        for i in range(len(data["features"])):
            prod = data["features"][i]["properties"]["productIdentifier"]
            #print(prod, data["features"][i]["properties"]["storage"]["mode"])
            feature_id = data["features"][i]["id"]
            try:
                storage = data["features"][i]["properties"]["storage"]["mode"]
                platform = data["features"][i]["properties"]["platform"]
                resourceSize = int(data["features"][i]["properties"]["resourceSize"])
                if storage == "unknown":
                    print('found a product with "unknown" status : %s' % prod)
                    print("product %s cannot be downloaded" % prod)
                    print('please send and email with product name to peps admin team : exppeps@cnes.fr')
                else:
                    # recup du numero d'orbite
                    orbitN = data["features"][i]["properties"]["orbitNumber"]
                    if platform == 'S1A':
                        # calcul de l'orbite relative pour Sentinel 1A
                        relativeOrbit = ((orbitN - 73) % 175) + 1
                    elif platform == 'S1B':
                        # calcul de l'orbite relative pour Sentinel 1B
                        relativeOrbit = ((orbitN - 27) % 175) + 1

                    if orbit is not None:
                        if platform.startswith('S2'):
                            if prod.find("_R%03d" % orbit) > 0:
                                download_dict[prod] = feature_id
                                storage_dict[prod] = storage
                                size_dict[prod] = resourceSize

                        elif platform.startswith('S1'):
                            if relativeOrbit == orbit:
                                download_dict[prod] = feature_id
                                storage_dict[prod] = storage
                                size_dict[prod] = resourceSize
                    else:
                        download_dict[prod] = feature_id
                        storage_dict[prod] = storage
                        size_dict[prod] = resourceSize

            except:
                pass

        # cloud cover criterium:
        if collection[0:2] == 'S2':
            for i in range(len(data["features"])):
                prod = data["features"][i]["properties"]["productIdentifier"]
                if data["features"][i]["properties"]["cloudCover"] > clouds:
                    del download_dict[prod], storage_dict[prod], size_dict[prod]

        # selecion of specific satellite
        if sat != None:
            for i in range(len(data["features"])):
                prod = data["features"][i]["properties"]["productIdentifier"]
                if data["features"][i]["properties"]["platform"] != sat:
                    try:
                        del download_dict[prod], storage_dict[prod], size_dict[prod]
                    except KeyError:
                        pass

        for prod in download_dict.keys():
            print(prod, storage_dict[prod])
    else:
        print(">>> no product corresponds to selection criteria")
        # sys.exit(-1)
        return {}, {}, {}, {}
#    print(download_dict.keys())

    return(prod, download_dict, storage_dict, size_dict)


# ===================== MAIN
# ==================
# parse command line
# ==================

def parse_command_line():
    if len(sys.argv) == 1:
        prog = os.path.basename(sys.argv[0])
        print('      ' + sys.argv[0] + ' [options]')
        print("     Aide : ", prog, " --help")
        print("        ou : ", prog, " -h")
        print("example 1 : python %s -l 'Toulouse' -a peps.txt -d 2016-12-06 -f 2017-02-01 -c S2ST" %
              sys.argv[0])
        print("example 2 : python %s --lon 1 --lat 44 -a peps.txt -d 2015-11-01 -f 2015-12-01 -c S2" %
              sys.argv[0])
        print("example 3 : python %s --lonmin 1 --lonmax 2 --latmin 43 --latmax 44 -a peps.txt -d 2015-11-01 -f 2015-12-01 -c S2" %
              sys.argv[0])
        print("example 4 : python %s -l 'Toulouse' -a peps.txt -c SpotWorldHeritage -p SPOT4 -d 2005-11-01 -f 2006-12-01" %
              sys.argv[0])
        print("example 5 : python %s -c S1 -p GRD -l 'Toulouse' -a peps.txt -d 2015-11-01 -f 2015-12-01" %
              sys.argv[0])
        sys.exit(-1)
    else:
        usage = "usage: %prog [options] "
        parser = OptionParser(usage=usage)

        parser.add_option("-l", "--location", dest="location", action="store", type="string",
                          help="town name (pick one which is not too frequent to avoid confusions)", default=None)
        parser.add_option("-a", "--auth", dest="auth", action="store", type="string",
                          help="Peps account and password file")
        parser.add_option("-w", "--write_dir", dest="write_dir", action="store", type="string",
                          help="Path where the products should be downloaded", default='.')
        parser.add_option("-c", "--collection", dest="collection", action="store", type="choice",
                          help="Collection within theia collections", choices=['S1', 'S2', 'S2ST', 'S3'], default='S2')
        parser.add_option("-p", "--product_type", dest="product_type", action="store", type="string",
                          help="GRD, SLC, OCN (for S1) | S2MSI1C S2MSI2A S2MSI2Ap (for S2)", default="")
        parser.add_option("-m", "--sensor_mode", dest="sensor_mode", action="store", type="string",
                          help="EW, IW , SM, WV (for S1) | INS-NOBS, INS-RAW (for S3)", default="")
        parser.add_option("-n", "--no_download", dest="no_download", action="store_true",
                          help="Do not download products, just print curl command", default=False)
        parser.add_option("-d", "--start_date", dest="start_date", action="store", type="string",
                          help="start date, fmt('2015-12-22')", default=None)
        parser.add_option("-t", "--tile", dest="tile", action="store", type="string",
                          help="Sentinel-2 tile number", default=None)
        parser.add_option("--lat", dest="lat", action="store", type="float",
                          help="latitude in decimal degrees", default=None)
        parser.add_option("--lon", dest="lon", action="store", type="float",
                          help="longitude in decimal degrees", default=None)
        parser.add_option("--latmin", dest="latmin", action="store", type="float",
                          help="min latitude in decimal degrees", default=None)
        parser.add_option("--latmax", dest="latmax", action="store", type="float",
                          help="max latitude in decimal degrees", default=None)
        parser.add_option("--lonmin", dest="lonmin", action="store", type="float",
                          help="min longitude in decimal degrees", default=None)
        parser.add_option("--lonmax", dest="lonmax", action="store", type="float",
                          help="max longitude in decimal degrees", default=None)
        parser.add_option("-o", "--orbit", dest="orbit", action="store", type="int",
                          help="Orbit Path number", default=None)
        parser.add_option("-f", "--end_date", dest="end_date", action="store", type="string",
                          help="end date, fmt('2015-12-23')", default='9999-01-01')
        parser.add_option("--json", dest="search_json_file", action="store", type="string",
                          help="Output search JSON filename", default=None)
        parser.add_option("--windows", dest="windows", action="store_true",
                          help="For windows usage", default=False)
        parser.add_option("--cc", "--clouds", dest="clouds", action="store", type="int",
                          help="Maximum cloud coverage", default=100)
        parser.add_option("--sat", "--satellite", dest="sat", action="store", type="string",
                          help="S1A,S1B,S2A,S2B,S3A,S3B", default=None)
        parser.add_option("-x", "--extract", dest="extract", action="store_true",
                          help="Extract and remove zip file after download")
        parser.add_option("--trials", "--trials", dest="max_trials", action="store", type="int",
                          help="Maximum nunmber of trials when some products are on tape.", default=10)
        parser.add_option("--wait", "--wait", dest="wait", action="store", type="int",
                          help="Time to wait in minutes between each trial.", default=1)

        (options, args) = parser.parse_args()

        return options, args


def peps_download(write_dir, auth, collection='S2', product_type="", sensor_mode="", no_download=True,
                  start_date=None, end_date=None, tile=None, location=None,
                  lat=None, lon=None, latmin=None, latmax=None, lonmin=None, lonmax=None,
                  orbit=None, search_json_file=None, windows=False, clouds=100, sat=None, extract=False,
                  max_trials=10, wait=1):
    """
    Download Sentinel S1, S2 or S3 products from PEPS sever

    Parameters
    ----------
    write_dir: str
        Download directory
    auth: str
        Authentication file with Peps account and password
    collection: str
        Collection within theia collections: 'S1', 'S2', 'S2ST', 'S3'
    product_type: str
        GRD, SLC, OCN (for S1) | S2MSI1C S2MSI2A S2MSI2Ap (for S2)
    sensor_mode:
        EW, IW , SM, WV (for S1) | INS-NOBS, INS-RAW (for S3)
    no_download: bool
        Do not download products, just print curl command results
    start_date: str
        start date, in the format '2015-12-22'
    end_date: str
        end date, in the format '2015-12-22'
    tile: str
        Sentinel-2 tile number, e.g. 31TCJ or T31TCJ are allowed
    location: str
        town name, e.g. 'Toulouse'
    lat,lon: float
        latitude or longitude in decimal degrees
    latmin,latmax,lonmin,lonmax: float
        bounding box of an area of interest
    orbit: int
        Orbit Path number
    search_json_file: str
        Output search JSON file path
    windows: bool
        For windows usage
    clouds: int
        Maximum cloud coverage
    sat: str
        S1A,S1B,S2A,S2B,S3A,S3B
    extract: bool
        If True, extract and remove zip file after download
    max_trials: int
        Maximum number of trials before it stops although files are still not downloaded (on tape or staging)
    wait: int
        Number of minutes to wait between trials.

    Returns
    -------
    list
        Product names
    """

    if search_json_file is None or search_json_file == "":
        search_json_file = 'search.json'

    if sat != None:
        print(sat, collection[0:2])
        if not sat.startswith(collection[0:2]):
            SysError("input parameters collection and satellite are incompatible", -1)
            # sys.exit(-1)

    if tile is None:
        if location is None:
            if lat is None or lon is None:
                if (latmin is None) or (lonmin is None) or (latmax is None) or (lonmax is None):
                    raise SysError("provide at least a point or rectangle or tile number", -1)
                    # sys.exit(-1)
                else:
                    geom = 'rectangle'
            else:
                if (latmin is None) and (lonmin is None) and (latmax is None) and (lonmax is None):
                    geom = 'point'
                else:
                    raise SysError("please choose between point and rectangle, but not both", -1)
                    # sys.exit(-1)

        else:
            if (latmin is None) and (lonmin is None) and (latmax is None) and (lonmax is None) and (lat is None) or (lon is None):
                geom = 'location'
            else:
                raise SysError("please choose location and coordinates, but not both", -1)
                # sys.exit(-1)

    # geometric parameters of catalog request

    if tile is not None:
        if tile.startswith('T') and len(tile) == 6:
            tileid = tile[1:6]
        elif len(tile) == 5:
            tileid = tile[0:5]
        else:
            raise SysError("tile name is ill-formated : 31TCJ or T31TCJ are allowed", -4)
            # sys.exit(-4)
        query_geom = "tileid=%s" % (tileid)
    elif geom == 'point':
        query_geom = 'lat=%f\&lon=%f' % (lat, lon)
    elif geom == 'rectangle':
        query_geom = 'box={lonmin},{latmin},{lonmax},{latmax}'.format(
            latmin=latmin, latmax=latmax, lonmin=lonmin, lonmax=lonmax)
    elif geom == 'location':
        query_geom = "q=%s" % location

    # date parameters of catalog request
    if start_date is not None:
        start_date = start_date
        if end_date is not None:
            end_date = end_date
        else:
            end_date = date.today().isoformat()

    # special case for Sentinel-2

    if collection == 'S2':
        if start_date >= '2016-12-05':
            print("**** products after '2016-12-05' are stored in Tiled products collection")
            print("**** please use option -c S2ST")
        elif end_date >= '2016-12-05':
            print("**** products after '2016-12-05' are stored in Tiled products collection")
            print("**** please use option -c S2ST to get the products after that date")
            print("**** products before that date will be downloaded")

    if collection == 'S2ST':
        if end_date < '2016-12-05':
            print("**** products before '2016-12-05' are stored in non-tiled products collection")
            print("**** please use option -c S2")
        elif start_date < '2016-12-05':
            print("**** products before '2016-12-05' are stored in non-tiled products collection")
            print("**** please use option -c S2 to get the products before that date")
            print("**** products after that date will be downloaded")

    # ====================
    # read authentification file
    # ====================
    try:
        f = open(auth)
        (email, passwd) = f.readline().split(' ')
        if passwd.endswith('\n'):
            passwd = passwd[:-1]
        f.close()
    except Exception as e:
        print(e)
        SysError("error with authentication file", -2)
        # sys.exit(-2)


    if os.path.exists(search_json_file):
        os.remove(search_json_file)


    # ====================
    # search in catalog
    # ====================
    if (product_type == "") and (sensor_mode == ""):
        search_catalog = 'curl -k -o %s https://peps.cnes.fr/resto/api/collections/%s/search.json?%s\&startDate=%s\&completionDate=%s\&maxRecords=500' % (
            search_json_file, collection, query_geom, start_date, end_date)
    else:
        search_catalog = 'curl -k -o %s https://peps.cnes.fr/resto/api/collections/%s/search.json?%s\&startDate=%s\&completionDate=%s\&maxRecords=500\&productType=%s\&sensorMode=%s' % (
            search_json_file, collection, query_geom, start_date, end_date, product_type, sensor_mode)

    if windows:
        search_catalog = search_catalog.replace('\&', '^&')

    print(search_catalog)
    os.system(search_catalog)
    time.sleep(5)

    prod, download_dict, storage_dict, size_dict = parse_catalog(search_json_file, orbit, collection, clouds, sat)

    # ====================
    # Download
    # ====================


    if len(download_dict) == 0:
        print("No product matches the criteria")
    else:
        # first try for the products on tape
        if write_dir == None:
            write_dir = os.getcwd()

        for prod in list(download_dict.keys()):
            file_exists = os.path.exists(("%s/%s.SAFE") % (write_dir, prod)
                                         ) or os.path.exists(("%s/%s.zip") % (write_dir, prod))
            if (not(no_download) and not(file_exists)):
                if storage_dict[prod] == "tape":
                    tmticks = time.time()
                    tmpfile = ("%s/tmp_%s.tmp") % (write_dir, tmticks)
                    print("\nStage tape product: %s" % prod)
                    get_product = 'curl -o %s -k -u "%s:%s" https://peps.cnes.fr/resto/collections/%s/%s/download/?issuerId=peps &>/dev/null' % (
                        tmpfile, email, passwd, collection, download_dict[prod])
                    os.system(get_product)
                    if os.path.exists(tmpfile):
                        os.remove(tmpfile)

        NbProdsToDownload = len(list(download_dict.keys()))
        print("##########################")
        print("%d  products to download" % NbProdsToDownload)
        print("##########################")
        n_trials = 0
        while ((NbProdsToDownload > 0) and (n_trials < max_trials)):
            # redo catalog search to update disk/tape status
            if (product_type == "") and (sensor_mode == ""):
                search_catalog = 'curl -k -o %s https://peps.cnes.fr/resto/api/collections/%s/search.json?%s\&startDate=%s\&completionDate=%s\&maxRecords=500' % (
                    search_json_file, collection, query_geom, start_date, end_date)
            else:
                search_catalog = 'curl -k -o %s https://peps.cnes.fr/resto/api/collections/%s/search.json?%s\&startDate=%s\&completionDate=%s\&maxRecords=500\&productType=%s\&sensorMode=%s' % (
                    search_json_file, collection, query_geom, start_date, end_date, product_type, sensor_mode)

            if windows:
                search_catalog = search_catalog.replace('\&', '^&')

            os.system(search_catalog)
            time.sleep(2)

            prod, download_dict, storage_dict, size_dict = parse_catalog(search_json_file, orbit, collection, clouds, sat)

            NbProdsToDownload = 0
            # download all products on disk
            for prod in list(download_dict.keys()):
                file_exists = os.path.exists(("%s/%s.SAFE") % (write_dir, prod)
                                             ) or os.path.exists(("%s/%s.zip") % (write_dir, prod))
                if (not(no_download) and not(file_exists)):
                    if storage_dict[prod] == "disk":
                        tmticks = time.time()
                        tmpfile = ("%s/tmp_%s.tmp") % (write_dir, tmticks)
                        print("\nDownload of product : %s" % prod)
                        get_product = 'curl -o %s -k -u "%s:%s" https://peps.cnes.fr/resto/collections/%s/%s/download/?issuerId=peps' % (
                            tmpfile, email, passwd, collection, download_dict[prod])
                        print(get_product)
                        os.system(get_product)
                        # check binary product, rename tmp file
                        if not os.path.exists(("%s/tmp_%s.tmp") % (write_dir, tmticks)):
                            NbProdsToDownload += 1
                        else:
                            check_rename(tmpfile, prod, size_dict[prod], write_dir, extract)

                elif file_exists:
                    print("%s already exists" % prod)

            # download all products on tape
            for prod in list(download_dict.keys()):
                file_exists = os.path.exists(("%s/%s.SAFE") % (write_dir, prod)
                                             ) or os.path.exists(("%s/%s.zip") % (write_dir, prod))
                if (not(no_download) and not(file_exists)):
                    if storage_dict[prod] == "tape" or storage_dict[prod] == "staging":
                        NbProdsToDownload += 1
            n_trials += 1
            if (NbProdsToDownload > 0) and (n_trials < max_trials):
                print("##############################################################################")
                print("%d remaining products are on tape, lets's wait %d minutes before trying again" %
                      (NbProdsToDownload, wait))
                print("##############################################################################")
                time.sleep(wait*60)


        return download_dict.keys()

if __name__ == '__main__':

    options, args = parse_command_line()
    try:
        peps_download(**vars(options))
    except SysError as e:
        print(e)
        sys.exit(e.exit_code)
    except Exception as e:
        raise e

