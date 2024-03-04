import socket

import probcli.answerparser as answerparser

class ProBCli():

    def __init__(self, path):
        self.path = path
        self.is_connected = False

        self._socket = None

    def connect_socket(self, host='localhost', port=None):
        if self.is_connected:
            raise ValueError('Already connected')

        if port is None:
            port = 9000

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(('localhost', port))

        self.is_connected = True

    def close_socket(self):
        if not self.is_connected:
            raise ValueError('Not connected')

        self._socket.close()
        self.is_connected = False

    def send_prolog(self, prolog):
        self._socket.sendall(prolog.encode('utf-8') + b'\0')

    def send_halt(self):
        self._socket.sendall('halt.\0')

    def receive_prolog(self):
        data = b''
        while True:
            data += self._socket.recv(1024)
            if b'\1' in data:  # Prolog terminates with \1
                break
        data = data.decode('utf-8').strip('\0')
        answer, _ = answerparser.parse_term(data)
        return answer
