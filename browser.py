import os
import socket
import ssl
import urllib.parse
import tkinter

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18


class URL:
    def __init__(self, url):
        if url.startswith('data'):
            self.scheme = 'data'
            self.data_url = url
            return
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]
        if self.scheme == "https":
            self.port = 443
        else:
            self.port = 80
        if "/" not in url:
            url += "/"
        self.host, url = url.split("/", 1)
        if ':' in self.host:
            self.host, port = self.host.split(':', 1)
            self.port = int(port)
        if not self.scheme == 'file':
            url = "/" + url
        self.path = url

    def request(self):
        if self.scheme == "file":
            if not os.path.isfile(self.path):
                raise FileNotFoundError(f"File not found: {self.path}")
            with open(self.path, "r", encoding='utf-8') as f:
                return f.read()
        elif self.scheme == 'data':
            prefix = 'data:'
            data_content = self.data_url[len(prefix):]
            if ',' not in data_content:
                raise ValueError("Invalid data URL format")
            metadata, data = data_content.split(',', 1)
            decoded_data = urllib.parse.unquote(data)
            return decoded_data
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        s.connect((self.host, self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        request = f'GET {self.path} HTTP/1.1\r\n'
        headers = {
            'Host': self.host,
            'Connection': 'close',
            'User-Agent': 'CustomSimpleClient/1.0'
        }
        for header, value in headers.items():
            request += f'{header}: {value}\r\n'
        request += '\r\n'
        s.send(request.encode("utf-8"))
        response = s.makefile("r", encoding="utf-8", newline="\r\n")
        status_line = response.readline()
        version, status, explanation = status_line.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == '\r\n':
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()

        return content


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

    def load(self, url):
        body = url.request()
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(x, y - self.scroll, text=c)


def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x > WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list


def lex(body):
    text = ""
    in_tag = False
    i = 0
    while i < len(body):
        c = body[i]
        if c == '<':
            in_tag = True
            i += 1
        elif c == '>':
            in_tag = False
            i += 1
        elif not in_tag:
            if body.startswith('&lt', i):
                text += "<"
                i += 4
            elif body.startswith('&gt', i):
                text += ">"
                i += 4
            else:
                text += c
                i += 1
        else:
            i += 1
    return text


def load(url: URL):
    body = url.request()
    lex(body)


if __name__ == '__main__':
    import sys

    default_file = "/temp/test.html"
    if len(sys.argv) > 1:
        Browser().load((URL(sys.argv[1])))
    else:
        Browser().load((URL(f'file://{default_file}')))
    tkinter.mainloop()
