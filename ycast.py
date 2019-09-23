#!/usr/bin/env python3

import os
import sys
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import xml.etree.cElementTree as etree

import yaml

YCAST_LOCATION = 'ycast'

stations = {}


def get_stations():
    global stations
    ycast_dir = os.path.dirname(os.path.realpath(__file__))
    try:
        with open(ycast_dir + '/stations.yml', 'r') as f:
            stations = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        print("ERROR: Station configuration not found. Please supply a proper stations.yml.")
        sys.exit(1)


def text_to_url(text):
    return text.replace(' ', '%20')


def url_to_text(url):
    return url.replace('%20', ' ')


class YCastServer(BaseHTTPRequestHandler):
    def do_GET(self):
        get_stations()
        self.address = 'http://' + self.headers['Host']
        if 'loginXML.asp?token=0' in self.path:
            self.send_xml('<EncryptedToken>0000000000000000</EncryptedToken>')
        elif self.path == '/' \
                or self.path == '/' + YCAST_LOCATION \
                or self.path == '/' + YCAST_LOCATION + '/'\
                or self.path.startswith('/setupapp'):
            xml = self.create_root()
            for category in sorted(stations, key=str.lower):
                self.add_dir(xml, category,
                             self.address + '/' + YCAST_LOCATION + '/' + text_to_url(category))
            self.send_xml(etree.tostring(xml).decode('utf-8'))
        elif self.path.startswith('/' + YCAST_LOCATION + '/'):
            category = url_to_text(self.path[len(YCAST_LOCATION) + 2:].partition('?')[0])
            if category not in stations:
                self.send_error(404)
                return
            xml = self.create_root()
            for station in sorted(stations[category], key=str.lower):
                self.add_station(xml, station, stations[category][station])
            self.send_xml(etree.tostring(xml).decode('utf-8'))
        else:
            self.send_error(404)

    def send_xml(self, content):
        xml_data = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        xml_data += content
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', len(xml_data))
        self.end_headers()
        self.wfile.write(bytes(xml_data, 'utf-8'))

    def create_root(self):
        return etree.Element('ListOfItems')

    def add_dir(self, root, name, dest):
        item = etree.SubElement(root, 'Item')
        etree.SubElement(item, 'ItemType').text = 'Dir'
        etree.SubElement(item, 'Title').text = name
        etree.SubElement(item, 'UrlDir').text = dest
        return item

    def add_station(self, root, name, url):
        item = etree.SubElement(root, 'Item')
        etree.SubElement(item, 'ItemType').text = 'Station'
        etree.SubElement(item, 'StationName').text = name
        etree.SubElement(item, 'StationUrl').text = url
        return item


parser = argparse.ArgumentParser(description='vTuner API emulation')
parser.add_argument('-l', action='store', dest='address', help='Listen address', default='0.0.0.0')
parser.add_argument('-p', action='store', dest='port', type=int, help='Listen port', default=80)
arguments = parser.parse_args()
get_stations()
try:
    server = HTTPServer((arguments.address, arguments.port), YCastServer)
except PermissionError:
    print("ERROR: No permission to create socket. Are you trying to use ports below 1024 without elevated rights?")
    sys.exit(1)
print('YCast server listening on %s:%s' % (arguments.address, arguments.port))
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
print('YCast server shutting down')
server.server_close()
