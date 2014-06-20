from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlparse
from warnings import warn
import base64
import sys

from mustaine.encoder import encode_object
from mustaine.parser import Parser
from mustaine.protocol import Call, Fault
from mustaine._util import BufferedReader
from mustaine import __version__


class ProtocolError(Exception):
    """ Raised when an HTTP error occurs """
    def __init__(self, url, status, reason):
        self._url    = url
        self._status = status
        self._reason = reason

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<ProtocolError for %s: %s %s>" % (self._url, self._status, self._reason,)


class HessianProxy(object):

    def __init__(self, service_uri, credentials=None, key_file=None,
                cert_file=None, timeout=10, buffer_size=65535,
                error_factory=lambda x: x, overload=False, proxy_uri=None):
        self._headers = list()
        self._headers.append(('User-Agent', 'mustaine/' + __version__,))
        self._headers.append(('Content-Type', 'application/x-hessian',))

        if sys.version_info < (2,6):
            warn('HessianProxy timeout not enforceable before Python 2.6', RuntimeWarning, stacklevel=2)
            timeout = {}
        else:
            timeout = {'timeout': timeout}

        self._uri = urlparse(service_uri)
        self._proxy_uri = urlparse(proxy_uri) if proxy_uri is not None else self._uri
        if self._uri.scheme == 'http':
            self._client = HTTPConnection(self._proxy_uri.hostname,
                                          self._proxy_uri.port or 80,
                                          strict=True,
                                          **timeout)
        elif self._uri.scheme == 'https':
            self._client = HTTPSConnection(self._proxy_uri.hostname,
                                           self._proxy_uri.port or 443,
                                           key_file=key_file,
                                           cert_file=cert_file,
                                           strict=True,
                                           **timeout)
        else:
            raise NotImplementedError("HessianProxy only supports http:// and https:// URIs")

        # autofill credentials if they were passed via url instead of kwargs
        if (self._uri.username and self._uri.password) and not credentials:
            credentials = (self._uri.username, self._uri.password)

        if credentials:
            auth = 'Basic ' + base64.b64encode(':'.join(credentials))
            self._headers.append(('Authorization', auth))

        self._buffer_size = buffer_size
        self._error_factory = error_factory
        self._overload = overload
        self._parser = Parser()

    class __RemoteMethod(object):
        # dark magic for autoloading methods
        def __init__(self, caller, method):
            self.__caller = caller
            self.__method = method
        def __call__(self, *args):
            return self.__caller(self.__method, args)

    def __getattr__(self, method):
        return self.__RemoteMethod(self, method)

    def __repr__(self):
        return "<mustaine.client.HessianProxy(\"%s\")>" % (self._uri.geturl(),)

    def __str__(self):
        return self.__repr__()

    def __call__(self, method, args):
        try:
            self._client.putrequest('POST', self._uri.path)
            for header in self._headers:
                self._client.putheader(*header)

            request = encode_object(Call(method, args, overload=self._overload))
            self._client.putheader("Content-Length", str(len(request)))
            self._client.endheaders()
            self._client.send(str(request))

            response = self._client.getresponse()
            if response.status != 200:
                raise ProtocolError(self._uri.geturl(), response.status, response.reason)

            length = response.getheader('Content-Length', -1)
            if length == '0':
                raise ProtocolError(self._uri.geturl(), 'FATAL:', 'Server sent zero-length response')

            reply = self._parser.parse_stream(BufferedReader(response, buffer_size=self._buffer_size))
            self._client.close()

            if isinstance(reply.value, Fault):
                raise self._error_factory(reply.value)
            else:
                return reply.value
        except:
            self._client.close()
            raise
