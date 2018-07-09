from .fabricator import FabricatorRequestError, FabricatorRequestAuthError

# Simple response handlers that are available for use by clients when they define themselves
# ------------------------------------------------------------------------------------------------------------
def handler_json_decode(resp):
    """
    If no Fabricator response handler is provided, this one will be used by default.
    It will attempt to decode a JSON response, and will then return the result.
    """
    resp = handler_check_ok(resp)
    try:
        # Try to decode and return a JSON response
        return resp.json(), resp.status_code
    except ValueError:
        return resp.content, resp.status_code


def handler_check_ok(resp):
    """
    Simple response handler that checks for an error. Raises if an error occurred. Otherwise returns the entire response.
    """
    if not resp.ok:
        if resp.status_code in (401, 403):
            raise FabricatorRequestAuthError(code=resp.status_code, content=resp.content)

        raise FabricatorRequestError('HTTPError during request to {}'.format(resp.url), code=resp.status_code, content=resp.content)

    return resp

def no_auth(request):
    """
    Use this if no auth is desired
    """
    return request
# ------------------------------------------------------------------------------------------------------------