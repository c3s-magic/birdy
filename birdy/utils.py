from ._compat import urlparse, urlsplit, urljoin
import base64
from os.path import curdir, abspath, join

import logging
LOGGER = logging.getLogger('BIRDY')


def fix_local_url(url):
    """
    If url is just a local path name then create a file:// URL. Otherwise return url just as it is.
    """
    LOGGER.debug("fix url %s", url)
    if url is None:
        return None
    u = urlsplit(url)
    if not u.scheme:
        # build local file url
        path = u.path.strip()
        if path.startswith('/'):
            # absolute path
            url = urljoin('file://', path)
        else:
            # relative path
            url = urljoin('file://', abspath(path))
        LOGGER.debug("fixed url = %s", url)
    return url


def is_file_url(url):
    u = urlsplit(url)
    return not u.scheme or u.scheme == 'file'


def encode(url, mimetypes):
    """
    Read file with given url and return content. If mimetype of file is binary then encode content with base64.

    If url is not a file:// url return url itself.

    :return: encoded content string or URL or None
    """
    encoded = None
    u = urlsplit(url)
    if not u.scheme or u.scheme == 'file':
        with open(u.path, 'r') as fp:
            content = fp.read()
            # TODO: check all mimetypes ... use also python-magic to detect mime type
            if len(mimetypes) == 0 or mimetypes[0].lower() == 'application/xml'\
               or mimetypes[0].lower().startswith('text/'):
                LOGGER.debug('send content of %s', url)
                # TODO: need to fix owslib unicode and complex data type handling
                encoded = str(content)
            else:
                LOGGER.debug('base64 encode content of %s', url)
                encoded = base64.b64encode(content.encode())
    else:
        # remote urls as reference
        LOGGER.debug('send url %s', url)
        encoded = url
    return encoded
