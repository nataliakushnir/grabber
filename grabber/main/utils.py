import hashlib

import requests


def md5Checksum(url):
    m = hashlib.md5()
    r = requests.get(url)
    for data in r.iter_content(8192):
         m.update(data)
    return m.hexdigest()
