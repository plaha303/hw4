import pathlib
import socket
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import mimetypes
import json
from threading import Thread
from datetime import datetime
import logging


BASE_DIR = pathlib.Path('static')
STORAGE_DIR = BASE_DIR.joinpath('storage')
STORAGE_FILE = STORAGE_DIR.joinpath('data.json')


def send_data_to_socket(data):
    data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data_socket.sendto(data, ('localhost', 5000))

    data_socket.close()


class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(content_length)

        self.send_response(302)
        self.send_header('Location', 'message.html')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)

        match pr_url.path:
            case '/':
                self.send_html(BASE_DIR / 'index.html')
            case '/message.html':
                self.send_html(BASE_DIR / 'message.html')
            case _:
                file = BASE_DIR / pr_url.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html(BASE_DIR / 'error.html', 404)

    def send_html(self, file, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(file, 'rb') as f:
            self.wfile.write(f.read())

    def send_static(self, file):
        self.send_response(200)

        mt, *rest = mimetypes.guess_type(file)[0]
        if not mt:
            mt = 'text/plain'

        self.send_header('Content-Type', mt)
        self.end_headers()
        with open(file, 'rb') as f:
            self.wfile.write(f.read())


def run(server=HTTPServer, handler=HTTPHandler):
    address = ('', 3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def save_data(data):
    body = urllib.parse.unquote_plus(data.decode())

    try:
        payload = {str(datetime.now()): {k: v.strip() for k, v in [el.split('=') for el in body.split('&')]}}
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as df:
                data = json.load(df)
                data.update(payload)
                payload = data
        except Exception:
            pass
        finally:
            with open(STORAGE_FILE, 'w', encoding='utf-8') as df:
                json.dump(payload, df)
    except ValueError as e:
        logging.error(f'Field parse data {body} with error: {e}')
    except OSError as e:
        logging.error(f'Field write data {body} with error: {e}')


def run_socket_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    server_socket.bind(server)

    try:
        while True:
            data, address = server_socket.recvfrom(1024)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(threadName)s %(message)s')

    if not STORAGE_FILE.exists():
        with open(STORAGE_FILE, 'w', encoding='utf-8') as df:
            json.dump({}, df)

    thread_server = Thread(target=run)
    thread_server.start()

    thread_socket = Thread(target=run_socket_server('localhost', 5000))
    thread_socket.start()
