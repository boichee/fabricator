from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

from .__version__ import __version__

import functools
import json
import re
from builtins import *

import requests
import six
from future.utils import raise_from
from requests.auth import AuthBase

if six.PY2:
    import aenum as enum
elif six.PY3:
    import enum


# Utilities
def extract_parameters(kwargs, names, remove=False):
    """
    In a few cases, because of the dual modes of Fabricator, we need to allow
    any set of parameters to be passed into a method in one mode, while requiring
    parameters in another. This makes dealing with that situation a bit easier.

    TODO(blevenson): This has one downside - None is used as the initializer, 
    which will make it impossible to set the value of one of the parameters to
    None intentionally. Need to think about how to handle this situation.
    """
    out = [None] * len(names)
    for i, n in enumerate(names):
        if n in kwargs:
            out[i] = kwargs[n]
            if remove:
                del kwargs[n]

    return tuple(out)

def destructure_dict(d, *args, default=None):
    return tuple(d.get(a, default) for a in args)


def check_valid_methods(methods):
    for i, m in enumerate(methods):
        # Skip check if already an instance of HTTPMethods
        if isinstance(m, HTTPMethods):
            continue

        try:
            m = HTTPMethods(m)
            methods[i] = m
        except ValueError as exc:
            raise_from(FabricatorNotImplementedError('method "{}" is not valid'.format(m)), exc)

def add_if_set(kw, **kwargs):
    for n, v in kwargs.items():
        if v is not None:
            kw[n] = v
    return kw

def check_required_params(missing_values=(None,), **kwargs):
    for n, v in kwargs.items():
        if v in missing_values:
            raise ValueError('missing required keyword parameter "{}"'.format(n))

# Custom Exceptions and Error Types
quote_and_escape = lambda s: "'{}'".format(s.replace("'", r"\'")) if s is not None else 'None'

class FabricatorException(Exception):
    pass

class FabricatorNotImplementedError(FabricatorException):
    pass

class FabricatorRequestError(FabricatorException):
    def __init__(self, message=None, code=None, content=None):
        FabricatorException.__init__(self, message)
        self.message = message
        self.code = code
        self.content = content

    @property
    def json(self):
        try:
            return json.loads(self.content)
        except:
            return self.content


    def __repr__(self):
        # Make sure the "code" is properly formatted as either an int or 'None'
        code_value = 'None' if self.code is None else self.code
        return 'FabricatorRequestError({}, code={}, content={})'.format(quote_and_escape(self.message), code_value, quote_and_escape(self.content))

    def __str__(self):
        return 'FabricatorRequestError: {} - Code: {} - Content: {}'.format(self.message, self.code, self.json)


class FabricatorRequestAuthError(FabricatorRequestError):
    def __init__(self, code=None, content=None):
        FabricatorRequestError.__init__(self, code=code, content=content)
        self.message = 'Authentication failed'

class FabricatorUsageError(FabricatorException):
    pass

class FabricatorParamValidationError(FabricatorUsageError):
    def __init__(self, param=None, *args, **kwargs):
        super(FabricatorParamValidationError, self).__init__(*args, **kwargs)
        self.param = param

    def __repr__(self):
        return 'FabricatorParamValidationError(param={})'.format(quote_and_escape(self.param))

    def __str__(self):
        return 'required parameter {} is missing'.format(self.param)


# HTTPMethods is used to ensure correct method names are being used when registering request methods and calling them
class HTTPMethods(enum.Enum):
    """The set of valid HTTP methods"""
    # Most commonly used for REST APIs
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'

    # Less frequently used in REST APIs
    OPTIONS = 'OPTIONS'
    HEAD = 'HEAD'
    CONNECT = 'CONNECT'
    TRACE = 'TRACE'

    def __eq__(self, other):
        if self is other:
            return True

        if self.value == other:
            return True

        return False

    @staticmethod
    def all():
        return tuple(v for v in dir(HTTPMethods) if not v.startswith('__'))

noop_auth_handler = lambda r: r


def make_auth_handler(f):
    """
    Creates an AuthBase class
    :param callable or AuthBase f: The function that will process the request and add auth details
    :return AuthBase: The AuthBase class
    """
    class AuthReady(AuthBase):
        def __call__(self, req):
            return f(req)

    return AuthReady

# The FabricatorEndpoint type represents a particular 'path' and HTTP method (or route in ReST terms) that requests can be sent to.
# This class actually makes the requests that occur in this library.
class FabricatorEndpoint:
    def __init__(self,
                 parent,
                 name=None,
                 path=None,
                 handler=None,
                 methods=None,
                 auth_handler=None,
                 headers=None,
                 required_params=()):
        """
        This creates a "Route" (really a known operation) within the Fabricator where it lives.
        """
        check_required_params(name=name, path=path)

        self.parent = parent
        self.name = name
        self.path = path
        self.handler = handler
        self.methods = methods
        self.auth_handler = auth_handler
        self.headers = headers
        self.required_params = required_params

    def __getattr__(self, item):
        self._check_method(item)
        return functools.partial(self._make_request, method=item)

    def __call__(self, *args, **kwargs):
        """
        If a class instance is called, then a request is made with the "default" method (first in list)
        """
        return self._make_request(method=self.methods[0], **kwargs)

    def _check_method(self, m):
        """
        Checks to make sure that the provided method is valid for this route
        """
        if isinstance(m, str):
            m = m.upper()

        if self.methods and m not in self.methods:
            raise FabricatorNotImplementedError('{} is not a valid method for the {} route'.format(m, self.path))

    def _get_response_handler(self):
        if self.handler is not None:
            return self.handler

        # No handler set on the route itself, so we need to look at the Fabricator parent, etc
        current = self.parent
        handler = None
        while handler is None and current is not None:
            handler = current._default_handler
            current = current._parent

        return handler or noop_response_handler # If no handler found in tree, default to noop response handler

    def _get_auth_handler(self):
        if self.auth_handler is not None:
            return make_auth_handler(self.auth_handler)

        current = self.parent
        auth_handler = None
        while auth_handler is None and current is not None:
            auth_handler = current._auth_handler
            current = current._parent

        ah = auth_handler or noop_auth_handler
        return make_auth_handler(ah)

    def _get_headers(self):
        if self.headers is not None:
            return self.headers

        current = self.parent
        headers = None
        while headers is None and current is not None:
            headers = current._headers
            current = current._parent

        h = headers or {}
        return h

    def _construct_url(self, url_params=None):
        # Handle URL params as necessary
        path = self.path
        for k, v in url_params.items():
            try:
                v = str(v)
            except:
                raise FabricatorUsageError('URL parameter could not be converted to str')

            path = path.replace(k, v)

        # Construct the full URL base by climbing through the Fabricator instance chain and adding together the base_url values
        current = self.parent
        base_url = ''
        while current is not None:
            base_url = current._base_url + base_url
            current = current._parent

        return '{}{}'.format(base_url, path)

    def _make_request(self, method, **kwargs):
        # Check to ensure the method is valid
        self._check_method(method)

        if isinstance(method, HTTPMethods):
            # method is actually a HTTPMethod enum, so get the string representation
            method = method.value
        elif isinstance(method, six.string_types):
            # method is already a string, make sure its uppercased the way that requests likes it
            method = method.upper()
        else:
            # Something went very very wrong if we're here. Most likely the user called _make_request directly. Bad user!
            raise FabricatorException('"method" ({}) is an invalid type: {}'.format(method, type(method)))

        # Check that all required arguments are present and accounted for
        for p in self.required_params:
            if p not in kwargs:
                raise FabricatorParamValidationError(param=p)

        # Before we continue, we need to check the path and see if it has any URL params in it, If so, we need to try to find those params in kwargs
        url_params = {}
        matches = re.findall('(:[A-z_]+)', self.path)
        for m in matches:
            if m[1:] not in kwargs:
                raise FabricatorParamValidationError(param=m)

            # Add to url_params and delete from kwargs
            url_params[m] = kwargs[m[1:]]
            del kwargs[m[1:]]

        options = {}
        if kwargs:
            if method in (HTTPMethods.POST, HTTPMethods.PUT, HTTPMethods.PATCH):
                options['json'] = kwargs
            else:
                # TODO: When passing query string params, need to make sure all values in kwargs are ok in terms of type
                options['params'] = kwargs

        # Now we want to set up headers and auth
        options['auth'] = self._get_auth_handler()()
        options['headers'] = self._get_headers()

        # Get session and request base from the Fabricator this route belongs to
        resp = requests.request(method, self._construct_url(url_params=url_params), **options)
        return self._get_response_handler()(resp)


# The noop handler is the default if no other handler is provided. It is just a passthrough.
noop_response_handler = lambda r: r

# The Fabricator class is a logical construct. It "contains" 1 or more "FabricatorEndpoint" instances. It also provides a gateway to
# using those instances for the end user. When the end user says something like 'api.authenticateUser' this class
# proxies the request to the correct FabricatorEndpoint instance automatically.
class Fabricator:
    """
    The Fabricator class serves 2 functions:
    1) In its initial mode, it allows endpoints to be registered to the client. Then, once .start() is called,
    2) It allows an end user to use those endpoints to contact an API
    """
    def __init__(self,
                 base_url,
                 auth_handler=None,
                 headers=None,
                 handler=None,
                 parent=None):
        self._parent = parent
        self._base_url = base_url
        self._auth_handler = auth_handler
        self._headers = headers
        self._default_handler = handler

        # Initialize the routes dict
        self._endpoints = {}
        self._started = False

    def __getattr_builder(self, name):
        """
        Looks up the correct attribute in "builder" mode. That is, finds the 
        correct HTTP method and returns a proxy to the register method.
        """
        if name.upper() not in HTTPMethods.all():
            all_methods = ', '.join(HTTPMethods.all()).lower()
            raise FabricatorUsageError('Endpoint registrations use the methods "{}"'.format(all_methods))

        return functools.partial(self.register, methods=[HTTPMethods(name.upper())])
    
    def __getattr_started(self, name):
        """
        Once the Fabricator client has been started, this looks up the correct
        endpoint in the map and returns that FabricatorEndpoint instance.
        """
        if name not in self._endpoints:
            raise FabricatorNotImplementedError('There is no method with the name "{}"'.format(name))

        return self._endpoints[name]

    def __getattr__(self, name):
        """
        Either:
        a) Finds the appropriate route based on the name of the attribute
        b) If the attr is the name of a HTTP Method, it will call register with that method
        """
        if self._is_started():
            return self.__getattr_started(name)
        return self.__getattr_builder(name)

    def add_header(self, **kwargs):
        """
        Adds a header to this Fabricator instance. Once added, header will be
        applied to all calls made to endpoints attached to this instance.
        Parameters:
        name (str): Header name
        value (str): Header value
        """
        if self._is_started():
            # If already started, assumes there is some endpoint called add_header
            return self.__getattr_started('add_header')(**kwargs)

        if 'name' in kwargs:
            d = { kwargs['name']: kwargs['value'] }
        else:
            d = kwargs

        if self._headers is None:
            self._headers = d
        else:
            self._headers.update(d)
        
        return self

    def set_handler(self, *args, **kwargs):
        if self._is_started():
            return self.__getattr_started('set_handler')(**kwargs)

        if 'handler' in kwargs:
            handler = kwargs['handler']
        else:
            handler = args[0]

        self._default_handler = handler

    def set_auth_handler(self, *args, **kwargs):
        if self._is_started():
            return self.__getattr_started('set_auth_handler')(**kwargs)

        if 'handler' in kwargs:
            handler = kwargs['handler']
        else:
            handler = args[0]
        
        self._auth_handler = handler

    def group(self, **kwargs):
        """
        Creates a new instance of this class so it can behave as a "subgroup" of the larger instance
        Parameters:
        name (str): The name of the group. Will become a method in the eventual client
        prefix (str): The path prefix this group represents in the API
        handler (Callable): Responses will be processed by this handler
        auth_handler (Callable): Requests will be pre-processed by this handler
        headers (Dict): Headers to add to all requests in this group
        """
        if self._is_started():
            return self.__getattr_started('group')(**kwargs)

        # Create the new Fabricator instance with self as the parent
        name, prefix = destructure_dict(kwargs, 'name', 'prefix')
        del kwargs['name']
        if prefix is not None:
            # In 'group' we call the 'base_url' a 'prefix'. Translate before calling.
            kwargs['base_url'] = prefix
            del kwargs['prefix']
        self._endpoints[name] = Fabricator(parent=self, **kwargs)

        # Return it to the caller so they can use it
        return self._endpoints[name]

    def start(self, **kwargs):
        """
        Freezes the Fabricator so no more routes can be added
        """
        # Since "start" is a reasonable name for an endpoint, check to make
        # sure we haven't already been started before continuing. If start() has
        # already been called, then this was intended to be an endpoint call
        if self._is_started():
            return self.__getattr_started('start')(**kwargs)
        
        # Not yet started, so do so. If this is called on a group, rather than
        # a parent, the root will be found so the entire client is started as
        # well.
        self._find_root()._started = True
    
    def _find_root(self):
        """
        If the current instance is a child group, work up to the root and then
        return the root instance
        """
        current = self
        while current._parent:
            current = current._parent
        return current

    def _is_started(self):
        # Work up through the tree, checking to see if the Fabricator is marked as "ready"
        current = self
        while current is not None:
            if current._started:
                return True
            current = current._parent

        return False

    def standard(self, with_param=None, **kwargs):
        """
        Many ReST APIs follow the form:
        GET /       all
        GET /:id    get
        POST /      create
        PUT /:id    overwrite
        PATCH /:id  update
        DELETE /:id delete

        This method will create all of these routes in a single operation, giving
        them the names listed on the right side of the table
        """
        if self._is_started():
            # Fabricator client has been started, so pass off control
            kwargs = add_if_set(kwargs, with_param=with_param)
            return self.__getattr_started('standard')(**kwargs)

        # Create the All and Create methods
        self.register(name='all', path='/', methods=['GET'], **kwargs)
        self.register(name='create', path='/', methods=['POST'], **kwargs)

        # If with_param was set, use it to create the rest of the methods
        if with_param:
            path = '/:{}'.format(with_param)
            self.register(name='get', path=path, methods=['GET'])
            self.register(name='overwrite', path=path, methods=['PUT'])
            self.register(name='update', path=path, methods=['PATCH'])
            self.register(name='delete', path=path, methods=['DELETE'])

    def register(self, **kwargs):
        """
        Registers a new route into the Fabricator

        Parameters:
        name (str): The name of the route
        path (str): The path
        methods (List[str]): The methods that should be registered under this endpoint
        handler (Callable): A handler that should be applied to the response
        auth_handler (Callable): A handler that should be applied to the request to handle authentication
        headers (Dict): Headers that should be added to the request
        required_params (List[str]): A list of parameters that must be present when this endpoint is called 
        """
        # Check for started
        if self._is_started():
            return self.__getattr_started('register')(**kwargs)
        
        name, path, methods = destructure_dict(kwargs, 'name', 'path', 'methods')
        
        # Check that the provided methods are valid
        check_valid_methods(methods)

        if not path.startswith('/'):
            path = '/' + path

        # Now register the route to the name
        self._endpoints[name] = \
            FabricatorEndpoint(parent=self, **kwargs)
        
        # Return self to allow calls to be chained
        return self

