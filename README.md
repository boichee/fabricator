## Fabricator

Have an API? Make a client.

### What is it?

`fabricator` provides a fast, declarative-ish interface for creating clients for APIs. Create clients for ReST APIs in just a few lines of code.

### I don't believe you, show me...

Ok, fine. I'll show you.

First, you'll need to install fabricator. It's been tested to be compatible with Python 2.7 and 3.6.

#### First, install `fabricator`

**Install with `pip` (Recommended)**

`pip install fabricate-it`

**or, just clone it into your project**

`git submodule add http://github.com/boichee/fabricator.git`

#### Now, use `fabricator`

In this example, we'll create a client that works with an imaginary "Todo" API (I know, boring example...)
Imagine we have a "Todo API" (I know, boring example) that looks like this:

```
GET     /__health
GET     /api/v1/todos/
GET     /api/v1/todos/:id
POST    /api/v1/todos/
PUT     /api/v1/todos/:id
DELETE  /api/v1/todos/:id
```

You can create a client for all of these endpoints like this:

```python
from fabricator import Fabricator

def MyTodoAPI():
    # Establish a client instance using the Fabricator class
    client = Fabricator(base_url='https://todos.com')
    
    # Now, you start adding your endpoints
    client.get(name='health', path='/__health')
    
    # Endpoints for the To-Do resource
    # Note: You don't have to create a group, but its a nice feature that saves some typing and 
    # allows you to group handlers and other features (more on that later)
    todos = client.group(name='todos', prefix='/api/v1/todos') 
    
    # Now that we have a group, we can create endpoints within it
    todos.get(name='all', path='/')
    todos.get(name='one', path='/:id')
    todos.post(name='create', path='/')
    todos.put(name='update', path='/:id')
    todos.delete(name='remove', path='/:id')
    
    # .start() locks the Client and prepares it for use.
    client.start()
    
    # And return it, of course
    return client
```

Actually, since this CRUD structure is so common in ReSTful APIs, there's a shortcut
method to create APIs that have this topology - `.standard()`:

```python
from fabricator import Fabricator

def MyTodoAPI():
    # Establish a client instance using the Fabricator class
    client = Fabricator(base_url='https://todos.com')
    
    # Now, you start adding your endpoints
    client.get(name='health', path='/__health')
    
    # Create the group
    todos = client.group(name='todos', prefix='/api/v1/todos')

    # Now create all the endpoints in one go
    # Note when using this shortcut the endpoints will have the names:
    # all, get, create, overwrite, update, delete
    todos.standard(with_param='id')
    
    # .start() locks the Client and prepares it for use.
    client.start()
    
    # And return it, of course
    return client
```

Ok, that's great. But how do I use that? Glad you asked...

```python
from fabricator.exc import *
client = MyTodoAPI()

# Let's try doing a health check with our new API
resp = client.health() # The `resp` object is a standard requests.Response instance
print("Status code was: %s" % resp.status_code)

# Ok, now something more complicated, let's create 5 todos
for i in range(5):
    s = 'Thing to do #{}'.format(i)
    resp = client.todos.create(value=s)
    if resp.status_code is not 201:
        print('The todo was not created!')
        exit(1)
    else:
        print('Successfully created Todo #{}'.format(i))
    
# Ok, but how do I find one of the todos?
# Note that the param 'id' is the same as the ':id' we used above
resp = client.todos.one(id=1)
if resp.status_code is not 200:
    print('Could not get the Todo!')
    exit(1)
    
# Extract the data
first_todo = resp.json()

# first_todo is now a dict with the form { 'id': 1, 'value': 'A thing to do' }
first_todo['value'] = 'Go outside and see the sun!'

# Let's update the todo
resp = client.todos.update(**first_todo)
if resp.status_code is not 200:
    print('The todo with ID %s did not update as expected' % first_todo['id'])
    exit(1)
    
# Actually, who needs it! I can remember to go outside on my own!
_, status_code = client.todos.remove(id=1)
if status_code is not 204:
    print('The Todo with ID 1 was not removed. Oh no!')

```

Wow, right?


### Response Handlers

You may not want callers to have access to, or to work directly with, the `requests.Response` object when a call is made. Maybe you want to do some response handling?

#### Use a response handler

A response handler is just a function with the signature `Callable[[request.Response], Any]`

Fabricator provides some default response handlers for you to use:

- `handler_json_decode`
- `handler_check_ok`

```python
from fabricator import Fabricator, handler_json_decode
client = Fabricator(base_url='https://todos.com', handler=handler_json_decode)
```

This `handler_json_decode` handler is super simple and is just provided for convenience. It does 3 things:

  1. It checks the result of each request, and makes sure the status code was in the 200 or 300 range. If it's not, an `FabricatorRequestError` or `FabricatorRequestAuthError` is raised (if auth was the problem).
  2. If the request was successful, it will try to decode the body of the request under the assumption it contains `json` data. If that works, it will parse the JSON into python objects. If it doesn't work, it falls back to returning the raw body as a string. 
  3. As long as no request error occurred, it returns a tuple with the form `(response_body, response_status_code)`.

I mention this because it's likely that your API will have some unique differences or you might want your client to return things in a different form.

#### Writing your own response handler

You can see an example of a custom response handler that effectively creates DAO's. It's in `examples/examples.py`. Here's the gist:

```python
# A response handler will receive the `requests.Response` instance that comes back from the HTTP request. It's up to you what to do with it.

# Imagine we want to create a MyTodo class and have all responses auto-converted into an instance

class MyTodo:
    def __init__(self, id, value):
        self.id = id
        self.value = value
        
def handler_todo_response(resp):
    if not resp.ok:
        return None
        
    try:
        data = resp.json()
        return MyTodo(**data)
    except:
        return None
        
from fabricator import Fabricator
client = Fabricator(base_url='https://todos.com', handler=handler_todo_response)

# You can set response handlers at any level. So they can be applied to a group, or just
# a single endpoint, if desired.

todos = client.group(name='todos', prefix='/api/v1/todos', handler=handler_todo_response)

# or...

todos.get(name='one', path='/:id', handler=handler_todo_response)

```

In the example above, if you only apply the handler to a `group`, but not to the parent API, the parent API will use whatever handler it received on endpoints outside of that group. Same goes for a handler set on a specific endpoint--only that endpoint will use the handler if you didn't set the handler at a higher level.

#### The `no-op` response handler

If you don't provide a value for `handler` when initializing your API, the default is to use the `no-op` response handler. This literally just returns the `requests.Response` instance that the python `requests` module generates.

If you don't provide a response handler when initializing a `Fabricator` (or using `client.set_handler()`), you're going to want to do this instead:

```python
from fabricator import Fabricator
client = Fabricator(base_url='https://todos.com')
client.get('health', path='/__health')
client.start()

# Call is the same, but notice we're now only expecting a single value as the response
resp = client.health()

# If you want the status code, do
print(resp.status_code)

# If you want the response text, you can do
print(resp.text)

# Response json? Sure:
print(resp.json())

# Want to know what else there is? Check out the docs for the `requests` package
``` 

#### Setting a `handler` after instantiation

You can set a `handler` after you instantiate the client with `set_handler`:

```python
status_code_handler = lambda r: r.status_code

client = Fabricator(...)
client.set_handler(handler=status_code_handler)
```


### What about auth?

Most API's do require that you authenticate yourself somehow. To do so here, you create an `auth_handler`. An Auth Handler has the signature:

`Callable[[requests.Request], requests.Request]`

Basically, your auth handler will receive the `Request` instance that is about to be sent to the API, and you can modify any part of it to make auth work properly. 

`fabricator` provides a basic auth handler for `JWT` auth. But it's easy to write your own. Let's imagine, for example, that rather than using the `Bearer` scheme, your API prefixes its tokens with `JWT`:

```python
import os

def jwt_auth_handler(req):
    req.headers['Authorization'] = 'JWT %s' % os.environ['AUTH_TOKEN']
    return req
``` 

That's it. Provide that, and every request will have an `Authorization` header added that looks like this:

`Authorization: JWT AAAAAAAAAABBBBBBBBBB`

You provide it when initializing your API, or group, or even a specific endpoint.

#### What if I don't want auth in some cases?

In the opposite case, where you don't want auth to happen on a specific endpoint--or within a particular group--you can just supply the provided `no_auth` auth handler. You do that like this:

```python
from fabricator import Fabricator
from fabricator.extras import no_auth

client = Fabricator(...)
client.post(name='login', path='/api/v1/auth/', auth_handler=no_auth)
```

#### Set 'auth_handler' after instantiation

Just like with response `handler`s, you can set an auth handler at any time using the `.set_auth_handler` method.

### Headers, anyone?

Headers can be provided at any level. At the top level `API()` instance creation. At the time you create an `client.group()`, or when registering an endpoint. It basically works the same as auth and handlers. Just provide a dict with the headers you want included:

```python
from fabricator import Fabricator

# Now every request will be set to have a content type of JSON unless you override at a deeper level
client = Fabricator(..., headers={ 'content-type': 'application/json' })
```

#### Can I add a header?

Yes, you can add a header at any time, to either the root client, or any group using the `.add_header` method.

```python
from fabricator import Fabricator

client = Fabricator(...)
client.add_header(name='X-CUSTOM_HEADER', value='custom_value')


# Or you can add to a group the same way
g = client.group(name='v1', prefix='/api/v1')
g.add_header(name='X-CUSTOM-HEADER', name='custom_value')
```

### Collisions

As of Fabricator 1.1.0, naming collisions are no longer a problem thanks to some additional magic. You can now name your endpoints whatever you'd like.

As a result, however, it's become more important that you always use keyword parameters when calling the builder functions. This means:

```python

# BAD. Don't do this.
client.get('one', path='/:id')
client.add_header('X-IP', '127.0.0.1')

# GOOD. Do this instead
client.get(name='one', path='/:id')
client.add_header(name='X-IP', value='127.0.0.1')

```

Failing to use keyword arguments when building clients with Fabricator can lead to unexpected behavior—**particularly if you mix and match keyword arguments and positional arguments**.

### Advanced Usage

Suppose you want to register an endpoint that works the same way with both the `PUT` and `PATCH` methods. `Fabricator` has a way to save some time:

```python
from fabricator import Fabricator

# Instantiate as usual
client = Fabricator(base_url='https://todos.com')

# Now, rather than using the magic ".put" or ".patch" methods, we're going to use ".register". 
# Fabricator uses this under the hood when you use ".put" or ".patch".
client.register(name='update', path='/todos/:id', methods=['PUT', 'PATCH'])

# Start the client as usual
client.start()

# Now you can use the update method to do a 'PUT' automatically (because 'PUT' was 1st in the list you provided above):
client.update(id=1, value='Important thing to remember')

# But what if I want to do a patch?
client.update.patch(id=1, value='Important thing to remember')

# What if I don't trust that it's really 'PUT'ing?
# Then you can do it explicitly!
client.update.put(id=1, value='Important thing to remember')

```

In fact, you can always call the execution methods explicitly if you want. But if you're only assigning 1 HTTP method to an endpoint method, there's no need.


### Running Tests

Fabricator uses `py.test`. To run the test-suite, do the following:

Make sure all dependencies are installed

```bash
pip install -r requirements.txt
```

Then run the tests

```bash
py.test
```

That's it.
