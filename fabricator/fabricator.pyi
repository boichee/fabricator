from typing import Callable, AnyStr, Optional, Any, Dict, List, Iterable, TYPE_CHECKING, Union

import requests
import six
from requests.auth import AuthBase

if six.PY2:
    import aenum as enum
elif six.PY3:
    import enum


if TYPE_CHECKING:
    # Types for annotations
    Request = requests.Request
    AuthFn = Callable[[Request], Request]
    ResponsePair = (Union[Dict, AnyStr], int)
    DecodedJSON = Union[List, Dict, AnyStr, None]
    ResponseHandler = Callable[[requests.Response], Any]

def quote_and_escape(s: AnyStr) -> AnyStr: ...

class FabricatorException(Exception): ...
class FabricatorNotImplementedError(FabricatorException): ...
class FabricatorUsageError(FabricatorException): ...


class FabricatorParamValidationError(FabricatorUsageError):
    param: AnyStr


class FabricatorRequestError(FabricatorException):
    message: AnyStr
    code: int
    content: AnyStr
    json: DecodedJSON
    def __init__(self,
                 message: Optional[AnyStr]=None,
                 *args: Any,
                 code: Optional[int]=None,
                 content: Optional[AnyStr]=None,
                 **kwargs: Dict[Any, Any]): ...


class FabricatorRequestAuthError(FabricatorRequestError):
    def __init__(self, code: Optional[int]=None, content: Optional[AnyStr]=None): ...


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

    def __eq__(self, other: Any) -> bool: ...

    @staticmethod
    def all() -> Iterable[AnyStr]: ...

# The FabricatorEndpoint type represents a particular 'path' and HTTP method (or route in ReST terms) that requests can be sent to.
# This class actually makes the requests that occur in this library.
class FabricatorEndpoint:
    parent: 'Fabricator'
    path: AnyStr
    name: AnyStr
    methods: List[HTTPMethods]
    auth_handler: AuthFn
    headers: Dict[AnyStr, AnyStr]
    handler: ResponseHandler
    required_params: List[AnyStr]

    def __init__(self, *,
                 parent: 'Fabricator',
                 name: AnyStr,
                 path: AnyStr,
                 handler: Optional[ResponseHandler]=None,
                 auth_handler: Optional[AuthFn]=None,
                 headers: Optional[Dict[AnyStr, AnyStr]]=None,
                 methods: Optional[List[HTTPMethods]]=None,
                 required_params: Optional[List[AnyStr]]=()): ...
    def __getattr__(self, item) -> Callable[[...], Any]: ...
    def __call__(self, *args: Any, **kwargs: Dict[AnyStr, Any]) -> ResponsePair: ...
    def _check_method(self, m: Union[AnyStr, HTTPMethods]) -> None: ...
    def _get_response_handler(self) -> ResponseHandler: ...
    def _get_auth_handler(self) -> AuthBase: ...
    def _get_headers(self) -> Dict[AnyStr, AnyStr]: ...
    def _construct_url(self, url_params: Dict[AnyStr, AnyStr]=None) -> AnyStr: ...
    def _make_request(self, method: Union[AnyStr, HTTPMethods], **kwargs: Dict[AnyStr, Any]) -> ResponsePair: ...

# The noop handler is the default if no other handler is provided. It is just a passthrough.
def noop_response_handler(r: requests.Response) -> requests.Response: ...

class Fabricator:
    _parent: 'Fabricator'
    _base_url: AnyStr
    _auth_handler: AuthFn
    _headers: Dict
    _routes: Dict[AnyStr, Union['Fabricator', FabricatorEndpoint]]
    _default_handler: ResponseHandler
    _started: bool

    def __init__(self, *,
                 base_url: AnyStr,
                 auth_handler: Optional[AuthFn]=None,
                 headers: Optional[Dict]=None,
                 handler: Optional[ResponseHandler]=None,
                 parent: 'Fabricator'=None): ...
    
    def __getattr_builder(self, name: AnyStr) -> Callable: ...
    def __getattr_started(self, name: AnyStr) -> Union[Fabricator, FabricatorEndpoint]: ...
    def __getattr__(self, item: AnyStr) -> Union[Fabricator, FabricatorEndpoint, Callable]: ...
    def group(self, *,
              name: AnyStr,
              prefix: AnyStr,
              auth_handler: Optional[AuthFn]=None,
              headers: Optional[Dict[AnyStr, AnyStr]]=None,
              handler: Optional[ResponseHandler]=None) -> 'Fabricator': ...

    def add_header(self, *, name: AnyStr, value: AnyStr): ...
    def set_handler(self, h_: ResponseHandler): ...
    def set_auth_handler(self, h_: AuthFn): ...
    def start(self): ...
    def _is_started(self) -> bool: ...
    def _find_root(self) -> 'Fabricator': ...
    def register(self, *,
                 name: AnyStr,
                 path: AnyStr='',
                 handler: Optional[ResponseHandler]=None,
                 methods: List[Union[AnyStr, HTTPMethods]]=None,
                 auth_handler: Optional[AuthFn]=None,
                 headers: Optional[Dict[AnyStr, AnyStr]]=None,
                 required_params: Optional[List[AnyStr]]=()) -> 'Fabricator': ...
