from aspen.sockets import FFFD
from aspen.sockets.buffer import ThreadedBuffer as Buffer
from aspen.sockets.message import Message
from aspen.testing.sockets import make_socket


def test_buffer_is_instantiable(mk):
    mk(('echo.sock.spt', 'socket.send(socket.recv())'))
    expected = Buffer
    actual = Buffer(make_socket(), 'foo').__class__
    assert actual is expected

def test_can_put_onto_buffer(mk):
    mk(('echo.sock.spt', 'socket.send(socket.recv())'))
    buffer = Buffer(make_socket(), 'foo')
    expected = [FFFD+'4'+FFFD+'1:::']
    buffer.put(Message.from_bytes('1:::'))
    actual = list(buffer.flush())
    assert actual == expected

def test_buffer_flush_performance():

    return # This test makes my lap hot.

    M = lambda: Message.from_bytes("3::/echo.sock:Greetings, program!")
    N = 10000
    buffer = Buffer([M() for i in range(N)])
    out = list(buffer.flush())
    nbuffer = len(buffer)
    nout = len(out)
    assert nbuffer + nout == N
    assert nout > 500



