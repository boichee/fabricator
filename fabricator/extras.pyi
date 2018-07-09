import requests

from .fabricator import DecodedJSON


# Simple response handlers that are available for use by clients when they define themselves
# ------------------------------------------------------------------------------------------------------------
def handler_json_decode(resp: requests.Response) -> (DecodedJSON, int): ...
def handler_check_ok(resp: requests.Response) -> requests.Response: ...
def no_auth(req: requests.Request) -> requests.Request: ...
# ------------------------------------------------------------------------------------------------------------