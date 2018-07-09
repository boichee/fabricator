import pytest
import requests_mock

from fabricator import Fabricator

BASE_URL = 'http://localhost'
HEALTH_TEST_URL = '{}/__health'.format(BASE_URL)

# Fixture for creating the Fabricator client
@pytest.fixture
def client() -> Fabricator:
    client = Fabricator(base_url=BASE_URL)
    return client

# Fixture for mocking requests as necessary
@pytest.fixture
def m():
    with requests_mock.Mocker() as m:
        yield m

def test_initialize_fabricator(client):
    assert isinstance(client, Fabricator)

def test_throws_on_bad_method(client):
    from fabricator.exc import FabricatorUsageError
    with pytest.raises(FabricatorUsageError):
        client.notahttpmethod(name='example', path='/example/')

def test_registers_method(client):
    client.get(name='example', path='/example/')
    assert 'example' in client._endpoints

def test_calling_registered_endpoint(client, m):
    # Mock the request we're going to be making
    m.get(HEALTH_TEST_URL, text='OK')

    # Register the endpoint to the client and start it
    client.get(name='health', path='/__health')
    client.start()

    # Call the endpoint and check the results
    resp = client.health()
    assert resp.status_code is 200
    assert resp.text == 'OK'

def test_calling_post_endpoint(client, m):
    # Mock the request
    m.post('{}/todos'.format(BASE_URL), text='OK')

    # Register the endpoint with the client
    client.post(name='create', path='/todos')
    client.start()

    # Call the endpoint
    resp = client.create(value='TEST VALUE')
    assert resp.status_code is 200

    # Now check the history
    assert m.last_request.json() == { 'value': 'TEST VALUE' }


def test_required_params_are_checked(client, m):
    """
    Make sure if required args are not available, an error is thrown
    """
    # Mock the request
    m.post('{}/todos'.format(BASE_URL), text='OK')

    # Set up the client
    client.post(name='create', path='/todos', required_params=('value',))
    client.start()

    # Call the endpoint
    from fabricator.exc import FabricatorParamValidationError
    with pytest.raises(FabricatorParamValidationError):
        resp = client.create(otherparam='TEST VALUE')


@pytest.fixture
def group(client):
    g = client.group(name='test', prefix='/test')
    return g

def test_group_is_child(group, client):
    """
    Make sure a newly created group is a child of client
    """
    assert group._parent is client


def test_group_can_have_registered_endpoints(client, group, m):
    group.get(name='test', path='/')
    assert 'test' in group._endpoints

    # Mock the call
    m.get('{}/test/'.format(BASE_URL), text='OK')

    # Start client
    client.start()

    resp = client.test.test()
    assert resp.status_code is 200



def test_headers_shared_from_endpoint_parent(client: Fabricator, m: requests_mock.Mocker):
    # Add a header to the top level client
    client.add_header('X-CUSTOM', '1')

    # Now add an endpoint
    client.get(name='health', path='/__health')
    client.start()

    # Mock the request
    m.get(HEALTH_TEST_URL, text='OK')

    # Make the request
    resp = client.health()
    assert resp.status_code is 200

    # Now check what was sent to the endpoint in the request
    assert m.last_request.headers['X-CUSTOM'] == '1'


def test_headers_sent_from_endpoint(client: Fabricator, m: requests_mock.Mocker):
    # Add an endpoint with a header
    client.get('health', path='/__health', headers={ 'X-CUSTOM': '1' })
    client.start()

    # Mock it
    m.get(HEALTH_TEST_URL, text='OK')

    # Make the request
    resp = client.health()
    assert resp.status_code is 200

    # Check that header was sent
    assert m.last_request.headers['X-CUSTOM'] == '1'


def test_direct_registration_with_multiple_methods(client: Fabricator, m: requests_mock.Mocker):
    # Add an endpoint using "register"
    client.register('update', path='/todos/:id', methods=['PUT', 'PATCH'])
    client.start()

    # Mock it
    m.request(requests_mock.ANY, '{}/todos/1'.format(BASE_URL), text='OK')

    def asrt(resp):
        assert resp.status_code is 200
        assert m.last_request.json()['value'] == 'Thing to do'

    # Test it
    resp = client.update.put(id=1, value='Thing to do')
    asrt(resp)

    resp = client.update.patch(id=1, value='Thing to do')
    asrt(resp)


def test_response_handler(client: Fabricator, m: requests_mock.Mocker):
    # Create and set a custom handler on the client
    def custom_handler(resp):
        return resp.text, resp.status_code

    client.set_handler(custom_handler)

    # Register an endpoint
    client.get('health', path='/__health')
    client.start()

    # Mock the request
    m.get(HEALTH_TEST_URL, text='OK')

    # Call the endpoint
    text, code = client.health()
    assert text == 'OK'
    assert code is 200






