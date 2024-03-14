import logging
import random
import socket
import subprocess
import time


def run_sicstus(command, load_file=None):
    args = ['sicstus']
    if load_file:
        args += ['-l', load_file]
    if command[-1] == '.':
        command = command[:-1]
    args += ['--goal', command + ',halt.']

    return subprocess.check_output(args, stderr=subprocess.PIPE).decode('utf-8').strip()


class BFuzzer():
    def __init__(self, bf_path):
        self.path = bf_path
        self.process = None
        self._socket = None

    def connect(self, existing_port=None):
        if not existing_port:
            args = ['sicstus', '-l', self.path,
                    '--goal', 'banditfuzz:run_bf_socket_server(_), halt.']
            logging.debug('Starting BFuzzer with args: %s', args)
            self.process = subprocess.Popen(args,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)

            # First line is the port number
            logging.debug('Waiting for port number')
            port_line = self.process.stdout.readline().decode('utf-8').strip()
            if port_line.startswith('Port: '):
                self.port = int(port_line[6:])
        else:
            self.port = existing_port

        # Connect to the socket
        logging.debug('Connecting to socket on port %d', self.port)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(('localhost', self.port))
        logging.debug('Connected to BanditFuzz')

    def disconnect(self):
        self._send_to_socket('halt.')
        if self._socket:
            self._socket.close()
        self._socket = None
        if self.process:
            self.process.terminate()
            self.process.wait()
        self.process = None

    def generate(self):
        """
        Generate a new B constraint.

        Returns
        -------
        wd : str
            The pretty printed predicate with well-definedness conditions.
        raw : str
            The raw AST of the generated B constraint.
        env : str
            The environment in which the B constraint was generated.
        """
        self._send_to_socket('generate.')
        answer = self._receive_from_socket()
        # Answer is three lines: generated AST, WD predicate, and environment
        lines = answer.split('\n')
        raw = lines[0][len('Raw: '):]
        wd = _deatomify(lines[1][len('WD: '):])
        env = lines[2][len('Env: '):]

        return wd, raw, env

    def list_actions(self, env):
        self._send_to_socket(f'list_actions({env}).')
        actions = self._receive_from_socket().strip()
        actions = actions.split(',')
        return actions

    def mutate(self, raw_pred, env, action):
        request = f"mutate({raw_pred},{env},{action})."
        self._send_to_socket(request)

        answer = self._receive_from_socket()
        # Answer is three lines: mutated AST, WD predicate, and environment
        lines = answer.split('\n')
        raw = _deatomify(lines[0][len('Raw: '):])
        wd = lines[1][len('WD: '):]
        new_env = lines[2][len('Env: '):]

        return wd, raw, new_env

    def init_random_state(self):
        """
        Initialize the random number generator state within Prolog with a
        random seed.
        """
        x = random.randint(1, 30268)
        y = random.randint(1, 30306)
        z = random.randint(1, 30322)
        b = random.randint(1, 1000000)
        self.set_random_state(x, y, z, b)
        return x, y, z, b

    def set_random_state(self, x, y, z, b):
        """
        Set the random number generator state within Prolog.
        As per the SICStus documentation, the state of the random number
        generator corresponds to a term random(X,Y,Z,B) where X is an integer
        in the range [1,30268], Y is an integer in the range [1,30306], Z is an
        integer in the range [1,30322], and B is a nonzero integer.
        """
        request = f'setrand({x},{y},{z},{b}).'
        self._send_to_socket(request)
        answer = self._receive_from_socket().strip()

        return answer

    def get_random_state(self):
        self._send_to_socket('getrand.')
        answer = self._receive_from_socket().strip()
        [x, y, z, b] = answer.split(',')
        return int(x), int(y), int(z), int(b)



    def _send_to_socket(self, message):
        # Ensure message ends with '.\n'
        if message[-1] != '\n':
            if message[-1] != '.':
                message += '.'
            message += '\n'
        elif message[-2] != '.':
            message = message[:-1] + '.\n'

        message += '\x00'

        self._socket.sendall(message.encode('utf-8'))

    def _receive_from_socket(self):
        data = b''
        while True:
            data += self._socket.recv(1024)
            if b'\x00' in data:
                break
        data = data.decode('utf-8').strip('\x00')

        return data

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()


def _deatomify(string):
    # Remove outer quotes
    return string[1:-1]
