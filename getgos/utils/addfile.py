import argparse
import hashlib
import sys
import logging
import tempfile
import urllib2
import time
import os

from ConfigParser import ConfigParser
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from getgos.utils.string import convert_bytes
from getgos.model import init_database, DBSession
from getgos.model.schema import File

# Initialize Logging
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)


def sumfile(fobj):
    m = hashlib.md5()
    while True:
        d = fobj.read(8096)
        if not d:
            break
        m.update(d)
    return m.hexdigest()


def md5sum(fname):
    try:
        f = file(fname, 'rb')
    except:
        return 'Fail'
    ret = sumfile(f)
    f.close()
    return ret


def main():
    parser = argparse.ArgumentParser(description='Add a file to get.galliumos.org')
    parser.add_argument('--file',
                        dest='file',
                        required=False,
                        type=unicode,
                        help="Path of file to add")
    parser.add_argument('--url',
                        dest='url',
                        required=False,
                        type=unicode,
                        help="URL of the file to download and add")
    parser.add_argument('--type',
                        dest='type',
                        choices=['nightly', 'beta', 'RC', 'release'],
                        required=True,
                        type=unicode,
                        help="Type of file")
    parser.add_argument('--device',
                        dest='device',
                        required=True,
                        type=unicode,
                        help="Target device")
    parser.add_argument('--fullpath',
                        dest='full_path',
                        required=False,
                        type=unicode,
                        help="Full path of file accessable via mirrors. Example: /cm/artifacts/123/build/update-cm-7.2.0-RC9-ace-signed.zip")
    parser.add_argument('--basepath',
                        dest='base_path',
                        required=False,
                        default="/opt/www/mirror/gos/",
                        help="Webroot of the mirror.")
    parser.add_argument('--config',
                        dest='config',
                        required=False,
                        default='/etc/getgos.ini',
                        help="Path to configuration file.")
    parser.add_argument('--timestamp',
                        dest='timestamp',
                        type=int,
                        required=False,
                        default=None,
                        help="Timestamp of build")

    args = parser.parse_args()
    config = ConfigParser()
    config.readfp(open(args.config, 'r'))
    args.db_uri = config.get('database', 'uri')

    if not args.base_path.endswith("/"):
        args.base_path = args.base_path + "/"

    if (not args.url and not args.file) or (args.url and args.file):
        logging.error("Must specify either --file or --url")
        parser.print_help()
        sys.exit(1)

    if args.url and not args.full_path:
        logging.error("Must specify --fullpath when using --url")
        parser.print_help()
        sys.exit(1)

    if args.url:
        args.file = download(args.url)
    else:
        args.file = os.path.abspath(args.file)

    logging.debug("Processing with arguments: %s", args)

    return process_file(args)


def download(url):
    tmpfn = tempfile.mktemp()
    logging.info("Downloading '%s' to '%s'", url, tmpfn)

    ud = urllib2.urlopen(url)
    total_bytes = float(ud.headers['Content-Length'])

    chunksize = 4096
    bytes_read = 0
    start_time = time.time()

    # Variables to keep track of progress.
    last_log = time.time()
    last_bytes = 0

    fd = open(tmpfn, "wb")
    while True:
        data = ud.read(chunksize)
        if not data:
            fd.close()
            break
        fd.write(data)
        bytes_read += len(data)
        last_bytes += len(data)

        if time.time() > last_log + 2:
            speed = convert_bytes((last_bytes / (time.time() - last_log)))
            percent_complete = (bytes_read / total_bytes) * 100

            logging.debug("Progress %0.2f%% @ %s/s", percent_complete, speed)

            # Reset
            last_log = time.time()
            last_bytes = 0

    elapsed = time.time() - start_time
    average_speed = total_bytes / elapsed
    logging.info("Downloaded %s in %0.0f seconds, average speed %s/s", convert_bytes(total_bytes), elapsed, convert_bytes(average_speed))

    return tmpfn


def process_file(args):
    init_database(create_engine(args.db_uri))
    session = DBSession()

    md5hash = md5sum(args.file)
    new = File.get_by_md5sum(md5hash)
    if new is None:
        new = File()
        new.md5sum = md5hash

    if args.url:
        new.filename = os.path.basename(args.url)
    else:
        new.filename = os.path.basename(args.file)

    if args.full_path:
        new.full_path = args.full_path
    else:
        new.full_path = args.file.replace(args.base_path, "")

    new.type = args.type
    new.size = os.path.getsize(args.file)
    new.device = args.device
    if args.timestamp is not None:
        new.date_created = datetime.fromtimestamp(args.timestamp)
    else:
        new.date_created = datetime.fromtimestamp(os.path.getmtime(args.file))

    logging.debug("Filename = %s", new.filename)
    logging.debug("Type = %s", new.type)
    logging.debug("Device = %s", new.device)
    logging.debug("MD5 = %s", new.md5sum)

    try:
        session.add(new)
        session.commit()
        logging.info("File added successfully!")
    except IntegrityError:
        session.rollback()
        logging.error("File already exists: '%s'", new.filename)

    if args.url:
        logging.info("Removing temporary file '%s'", args.file)
        os.remove(args.file)
