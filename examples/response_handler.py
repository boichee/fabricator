from fabricator import Fabricator
from fabricator.extras import handler_json_decode


def TodoClient():
    # Instantiate the Client
    client = Fabricator(base_url='https://todos.com', handler=handler_json_decode)

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
    _, code = client.health()
    if code is not 200:
        print('Something is wrong')
        return


    # First we'll create some todos
    for i in range(5):
        # In this example, the POST endpoint expects a JSON payload with a 'value'
        data, code = client.todos.create(value='My thing to do #{}'.format(i))
        if code is not 201:
            print('Something went wrong!')
            return

    # Ok, now let's get all of them and print them
    data, code = client.todos.all()
    for todo in data:
        print(todo)


    # How about we get just 1?
    todo, code = client.todos.one(id=1)
    print(todo)

    # Or we can update that item?
    todo['value'] = 'I forgot. I meant to write this.'
    _, code = client.todos.update(**todo)
    if code is not 202:
        print('Could not update todo. Oh no!')
        return

    # Eh, who needs it! I can just remember.
    client.todos.remove(id=1)


if __name__ == '__main__':
    example()