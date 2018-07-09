from fabricator import Fabricator


def TodoClient():
    # Instantiate the Client
    client = Fabricator(base_url='https://todos.com')

    # Health endpoint
    client.get('health', path='/__health')

    # Let's make a group to work with Todos
    todos = client.group(name='todos', prefix='/todos')

    # Now let's use the group
    todos.get('all', path='/')
    todos.get('one', path='/:id')
    todos.post('create', path='/')
    todos.put('update', path='/:id')
    todos.delete('remove', path='/:id')


    # Start the client
    client.start()

    return client


def example():
    client = TodoClient()

    # Let's check the health of the API to make sure its working
    resp = client.health()
    if resp.status_code is not 200:
        return

    # First we'll create some todos
    for i in range(5):
        # In this example, the POST endpoint expects a JSON payload with a 'value'
        resp = client.todos.create(value='My thing to do #{}'.format(i))
        if resp.status_code is not 201:
            print('Something went wrong!')
            return

    # Ok, now let's get all of them and print them
    resp = client.todos.all()
    data = resp.json()
    for todo in data:
        print(todo)


    # How about we get just 1?
    resp = client.todos.one(id=1)
    todo = resp.json()
    print(todo)

    # Or we can update that item?
    todo['value'] = 'I forgot. I meant to write this.'
    resp = client.todos.update(**todo)
    if resp.status_code is not 202:
        print('Could not update todo. Oh no!')
        return

    # Eh, who needs it! I can just remember.
    client.todos.remove(id=1)

if __name__ == '__main__':
    example()
