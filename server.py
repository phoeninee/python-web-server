import _thread
import socket
import urllib.parse

from utils import log

from models import SQLModel

from routes.index import (
    error,
)

# 用 from import as 来避免重名
from routes.index import route_dict as routes_index
from routes.todo import route_dict as routes_todo
from routes.admin import route_dict as routes_admin


# 定义一个 class 用于保存请求的数据
class Request(object):
    def __init__(self, raw_data):
        # 只能 split 一次，因为 body 中可能有换行
        header, self.body = raw_data.split('\r\n\r\n', 1)
        h = header.split('\r\n')

        parts = h[0].split()
        self.method = parts[0]
        path = parts[1]
        self.path = ""
        self.query = {}
        self.parse_path(path)
        log('Request: path 和 query', self.path, self.query)

        self.headers = {}
        self.cookies = {}
        self.add_headers(h[1:])
        log('Request: headers 和 cookies', self.headers, self.cookies)

    def add_headers(self, header):
        """
        Cookie: user=phoe
        """
        lines = header
        for line in lines:
            k, v = line.split(': ', 1)
            self.headers[k] = v

        if 'Cookie' in self.headers:
            cookies = self.headers['Cookie']
            for item in cookies.split('; '):
                k, v = item.split('=', 1)
                self.cookies[k] = v

    def form(self):
        body = urllib.parse.unquote_plus(self.body)
        log('form', self.body)
        log('form', body)
        args = body.split('&')
        f = {}
        log('args', args)
        for arg in args:
            k, v = arg.split('=')
            f[k] = v
        log('form() 字典', f)
        return f

    def parse_path(self, path):
        """
        输入: /post?message=hello&author=phoe
        返回
        (post, {
            'message': 'hello',
            'author': 'phoe',
        })
        """
        index = path.find('?')
        if index == -1:
            self.path = path
            self.query = {}
        else:
            path, query_string = path.split('?', 1)
            args = query_string.split('&')
            query = {}
            for arg in args:
                k, v = arg.split('=')
                query[k] = v
            self.path = path
            self.query = query


def response_for_path(request):
    """
    根据 path 调用相应的处理函数
    没有处理的 path 会返回 404
    """
    # 注册外部的路由
    r = routes_index()
    r.update(routes_todo())
    r.update(routes_admin())
    response = r.get(request.path, error)
    return response(request)


def process_connection(connection):
    with connection:
        r = connection.recv(1024)
        log('request log:\n <{}>'.format(r))
        r = r.decode()
        # 把原始请求数据传给 Request 对象
        request = Request(r)
        # 用 response_for_path 函数来得到 path 对应的响应内容
        response = response_for_path(request)
        log('response ready\n\n')
        # 把响应发送给客户端
        connection.sendall(response)


def run(host, port):
    """
    启动服务器
    """
    # 初始化 socket 套路
    # 使用 with 可以保证程序中断的时候正确关闭 socket 释放占用的端口
    log('开始运行于', 'http://{}:{}'.format(host, port))
    SQLModel.init_db()
    with socket.socket() as s:
        s.bind((host, port))
        # 无限循环来处理请求
        # 监听 接受 读取请求数据 解码成字符串
        s.listen()
        while True:
            connection, address = s.accept()
            log('ip <{}>\n'.format(address))
            _thread.start_new_thread(process_connection, (connection,))


if __name__ == '__main__':
    # 生成配置并且运行程序
    config = dict(
        host='localhost',
        port=3000,
    )
    run(**config)
