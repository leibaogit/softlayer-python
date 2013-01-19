# Copyright (c) 2010, SoftLayer Technologies, Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#  * Neither SoftLayer Technologies, Inc. nor the names of its contributors may
#    be used to endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
SoftLayer API bindings

See U{http://sldn.softlayer.com/article/Python}
"""

from urlparse import urlparse
import socket
import httplib
import xmlrpclib
import sys
import os

"""
@type API_USERNAME: C{str}
@var API_USERNAME: Your API username, if you wish to hardcode all API calls to
a single user.

@type API_KEY: C{str}
@var API_KEY: Your API key, if you wish to hardcode all API calls to a single
user.

@type API_PUBLIC_ENDPOINT: C{str}
@var API_PUBLIC_ENDPOINT: The base URL of the SoftLayer API's XML-RPC
endpoints over the public Internet.

@type API_PRIVATE_ENDPOINT: C{str}
@var API_PRIVATE_ENDPOINT: The base URL of the SoftLayer API's XML-RPC
endpoints over SoftLayer's private network.

@type API_BASE_URL: C{str}
@var API_BASE_URL: The base URL for the SoftLayer API's XML-RPC endpoints.
"""

API_USERNAME = None
API_KEY = None
API_PUBLIC_ENDPOINT = 'https://api.softlayer.com/xmlrpc/v3/'
API_PRIVATE_ENDPOINT = 'https://api.service.softlayer.com/xmlrpc/v3/'
API_BASE_URL = API_PUBLIC_ENDPOINT


class SoftLayerError(Exception):
    pass


class Client:
    """
    A SoftLayer API client

    Clients are intended to be declared once per service and used for all calls
    made to that service.

    @ivar _service_name: The name of the SoftLayer API service to query
    @ivar _endpoint_url: The base URL to the SoftLayer API's endpoints being
    used by this client.
    @ivar _headers: The headers to send to an API call
    @ivar _client: The xmlrpc client used to make calls
    """
    _prefix = "SoftLayer_"

    def __init__(self, service_name=None, id=None, username=None, api_key=None,
                 endpoint_url=None, timeout=None, verbose=False):
        """
        Create a SoftLayer API client

        @type service_name: C{str}
        @param service:name: The name of the SoftLayer API service to query.

        @type id: C{int}
        @param id: An optional object if if you're instantiating a particular
        SoftLayer_API object. Setting an id defines this client's
        initialization parameter.

        @type username: C{str}
        @param username: An optional API username if you wish to bypass the
        package's built-in username.

        @type api_key: C{str}
        @param api_key: An optional API key if you wish to bypass the package's
        built in API key.

        @type endpoint_url: C{str}
        @param endpoint_url: The API endpoint base URL you wish to connect to.
        Set this to API_PRIVATE_ENDPOINT to connect via SoftLayer's private
        network.
        """

        self.verbose = verbose
        self._service_name = service_name
        self._headers = {}

        # Set authentication
        self.username = username or API_USERNAME or os.environ.get('SL_USERNAME')
        self.api_key = api_key or API_KEY or os.environ.get('SL_API_KEY')

        if not all((self.username, self.api_key)):
            raise SoftLayerError(
                'Must supply username, api_key and service_name')

        self.set_authentication(self.username, self.api_key)

        if id is not None:
            self.set_init_parameter(int(id))

        self._endpoint_url = (endpoint_url or API_BASE_URL or \
            API_PUBLIC_ENDPOINT).rstrip('/')
        http_protocol = urlparse(self._endpoint_url).scheme

        if http_protocol == "https":
            self.transport = SecureProxyTransport()
        else:
            self.transport = ProxyTransport()

        if timeout is not None:
            self.transport.set_timeout(int(timeout))

    def add_raw_header(self, name, value):
        self.transport.raw_headers[name] = value

    def add_header(self, name, value):
        """
        Set a SoftLayer API call header

        Every header defines a customization specific to a SoftLayer API call.
        Most API calls require authentication and initialization parameter
        headers, but can also include optional headers such as object masks and
        result limits if they're supported by the API method you're calling.

        @type name: C{str}
        @param name: The name of the header to add

        @type value: C{dict}
        @param value: The header to add.
        """
        name = name.strip()

        if name is None or name is '':
            raise SoftLayerError('Please specify a header name.')

        self._headers[name] = value

    def remove_header(self, name):
        """
        Remove a SoftLayer API call header

        Removing headers may cause API queries to fail.

        @type name: C{str}
        @param name: The name of the header to remove.
        """

        name = name.strip()

        if name in self._headers:
            del self._headers[name]

    def set_authentication(self, username, api_key):
        """
        Set a user and key to authenticate a SoftLayer API call

        Use this method if you wish to bypass the API_USER and API_KEY class
        constants and set custom authentication per API call.

        See U{https://manage.softlayer.com/Administrative/apiKeychain} for more
        information.

        @type username: C{str}
        @param username: The username to authenticate an API call.

        @type api_key: C{str}
        @param api_key: The user's API key.
        """

        username = username.strip()
        api_key = api_key.strip()

        self.add_header('authenticate', {
            'username': username,
            'apiKey': api_key,
        })

    def set_init_parameter(self, id):
        """
        Set an initialization parameter header on a SoftLayer API call

        Initialization parameters instantiate a SoftLayer API service object to
        act upon during your API method call. For instance, if your account has
        a server with id number 1234, then setting an initialization parameter
        of 1234 in the SoftLayer_Hardware_Server Service instructs the API to
        act on server record 1234 in your method calls.

        See U{http://sldn.softlayer.com/article/Using-Initialization-Parameters-SoftLayer-API}
        for more information.

        @type id: C{int}
        @param id: The id number of the SoftLayer API object to instantiate
        """

        self.add_header(self._service_name + 'InitParameters', {
            'id': int(id)
        })

    def set_object_mask(self, mask):
        """
        Set an object mask to a SoftLayer API call

        Use an object mask to retrieve data related your API call's result.
        Object masks are skeleton objects, or strings that define nested
        relational properties to retrieve along with an object's local
        properties. See
        U{http://sldn.softlayer.com/article/Using-Object-Masks-SoftLayer-API}
        for more information.

        @type mask: C{dict}
        @param mask: The object mask you wish to define
        """

        header = 'SoftLayer_ObjectMask'

        if isinstance(mask, dict):
            header = '%sObjectMask' % self._service_name

        self.add_header(header, {'mask': mask})

    def set_result_limit(self, limit, offset=0):
        """
        Set a result limit on a SoftLayer API call

        Many SoftLayer API methods return a group of results. These methods
        support a way to limit the number of results retrieved from the
        SoftLayer API in a way akin to an SQL LIMIT statement.

        @type limit: C{int}
        @param limit: The number of results to limit a SoftLayer API call to.

        @type offset: C{int}
        @param offset: An optional offset to begin a SoftLayer API call's
        returned result at.
        """

        self.add_header('resultLimit', {
            'limit': int(limit),
            'offset': int(offset)
        })

    def __getitem__(self, name):
        """
        Get a SoftLayer Service

        @type name: C{str}
        @param name: The name of the service. E.G. SoftLayer_Account
        """
        if not name.startswith(self._prefix):
            name = self._prefix + name
        return Service(self, name)

    def __call__(self, service, method, *args, **kwargs):
        """
        Place a SoftLayer API call
        """
        headers = kwargs.get('headers', {})
        try:
            uri = '/'.join([self._endpoint_url, service])
            proxy = xmlrpclib.ServerProxy(uri, transport=self.transport,
                                          verbose=self.verbose)
            return proxy.__getattr__(method)({'headers': headers}, *args)
        except xmlrpclib.Fault, e:
            raise SoftLayerError(e.faultString)

    def __getattr__(self, name):
        """
        Attempt a SoftLayer API call

        Use this as a catch-all so users can call SoftLayer API methods
        directly against their client object. If the property or method
        relating to their client object doesn't exist then assume the user is
        attempting a SoftLayer API call and return a simple function that makes
        an XML-RPC call.
        """
        try:
            return object.__getattr__(self, name)
        except AttributeError:
            def call_handler(*args):
                return self(self._service_name, name, *args,
                    headers=self._headers)
            return call_handler

    def __repr__(self):
        key = "%sInitParameters" % (self._service_name,)
        if key in self._headers and "id" in self._headers[key]:
            return "<%r Instance [ID: %r]>" % (self._service_name,
                                               self._headers[key]['id'],)
        else:
            return "<%r Instance>" % (self._service_name,)


class Service:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def __call__(self, name, *args, **kwargs):
        id = kwargs.get('id')
        mask = kwargs.get('mask')
        headers = kwargs.get('headers')
        limit = kwargs.get('limit')
        offset = kwargs.get('offset', 0)

        if headers is None:
            headers = {
                'authenticate': {
                    'username': self.client.username,
                    'apiKey': self.client.api_key,
                }}

        if id is not None:
            headers[self.name + 'InitParameters'] = {'id': int(id)}

        if mask is not None:
            mheader = 'SoftLayer_ObjectMask'
            if isinstance(mask, dict):
                mheader = '%sObjectMask' % self.name
            headers[mheader] = {'mask': mask}


        if limit:
            headers['resultLimit'] = {
                    'limit': int(limit),
                    'offset': int(offset)
                }

        return self.client(self.name, name, headers=headers, *args)

    def __getattr__(self, name):
        try:
            return object.__getattr__(self, name)
        except AttributeError:
            def call_handler(*args, **kwargs):
                return self(name, *args, **kwargs)
            return call_handler

    def __repr__(self):
        return "<SoftLayer Service: %s>" % (self.name,)


class ProxyTransport(xmlrpclib.Transport):
    timeout = 15
    __extra_headers = {}

    def send_content(self, connection, request_body):
        for k, v in self.__extra_headers:
            connection.putheader(k, v)
        connection.putheader("Content-Type", "text/xml")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def set_timeout(self, timeout):
        self.timeout = timeout


class SecureProxyTransport(xmlrpclib.SafeTransport, ProxyTransport):
    def make_connection(self, host):
        try:
            if self._connection and host == self._connection[0]:
                return self._connection[1]
            # create a HTTPS connection object from a host descriptor
            # host may be a string, or a (host, x509-dict) tuple
            HTTPS = httplib.HTTPSConnection
            chost, self._extra_headers, x509 = self.get_host_info(host)
            self._connection = host, HTTPS(chost, None, **(x509 or {}))
            return self._connection[1]
        except AttributeError:
            host, extra_headers, x509 = self.get_host_info(host)
            try:
                HTTPS = httplib.HTTPS
            except AttributeError:
                raise NotImplementedError(
                    "your version of httplib doesn't support HTTPS"
                    )
            else:
                client = HTTPS(host, None, **(x509 or {}))
                client._conn.timeout = self.timeout
                return client
