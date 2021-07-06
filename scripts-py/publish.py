# -*- coding: utf-8 -*-

"""简单地自动化部署脚本，执行3个主要步骤
1. 编译golang程序
2. 构建、导出docker镜像
3. 上传镜像到ftps服务器
4. 删除中间文件
"""

import os
import sys
import subprocess
import ftplib
import ssl
import socket
from typing import Sized


class ImplicitFTPS(ftplib.FTP_TLS):
    _implicit_port = 990

    def __init__(self, host='', user='', passwd='', acct='',
                       keyfile=None, certfile=None, timeout: float = -999,
                       source_address=None, encoding='utf-8') -> None:
        self.context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        if keyfile and certfile:
            self.context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        self._prot_p = False

        self.host = host
        self.port = self._implicit_port
        self.timeout = timeout
        self.source_address = source_address
        self.encoding = encoding
        if host:
            self.connect()
            if user:
                self.login(user, passwd, acct)
                self.prot_p()

    def connect(self, host='', port=0, timeout: float = -999, source_address=None) -> str:
        if host:
            self.host = host
        if port:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        if self.timeout == 0:
            raise ValueError('Non-blocking socket (timeout=0) is not supported')
        if source_address:
            self.source_address = source_address
        self.sock = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        self.sock = self.context.wrap_socket(self.sock)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome


def do(protocol: str) -> None:
    if protocol == 'mqtt':
        os.chdir('../code/mqtt_prot_server/src/mqtt_prot_server')
    # elif protocol == 'tcp':
    #   os.chdir('../code/third_prot_server/src/third_prot_server')
    else:
        print(f'unsupported protocol: {protocol}')

    os.putenv('GOOS', 'linux')
    os.putenv('GOARCH', 'amd64')
    bin_name = os.path.basename(os.getcwd())
    img_name = f'{bin_name}:latest'
    tar_name = f'{bin_name}.tar'

    print('start building ...')
    
    try:
        subprocess.check_call(f'go build -ldflags "-s -w" {bin_name}')
        subprocess.check_call(f'docker build -t {img_name} .')
        subprocess.check_call(f'docker save {img_name} -o {tar_name}')
        subprocess.check_call('docker image prune -f')
    except subprocess.CalledProcessError as e:
        print(f'build error: {e}')
    else:
        print('build successfully!')
        send_ftps(tar_name)
    finally:
        try:
            subprocess.check_call('go clean')
            subprocess.check_call('go clean -cache')
            os.remove(tar_name)
        except subprocess.CalledProcessError as e:
            print(f'`go clean` error: {e}')
        except FileNotFoundError as e:
            pass


class ProgressIndicator:
    def __init__(self, file_size = 0) -> None:
        self.file_size = file_size
        self.sent_size = 0

    def __call__(self, sent_buf: Sized) -> None:
        self.sent_size += len(sent_buf)
        percent = self.sent_size / self.file_size * 100
        print(f'\ruploading progress: {percent:6.2f}%', end='')
        if percent >= 100:
            print()


def send_ftps(filename: str) -> None:
    print('start uploading over ftps ...')

    try:
        ftps = ImplicitFTPS(user='dingdx@teld.local',
                            passwd='Deri!20170713',
                            host='ftp.teld.cn',
                            timeout=3)
        ftps.cwd('/eys/huaweityun')
        with open(filename, 'rb') as f:
            ftps.storbinary(f'STOR {filename}', f, callback=ProgressIndicator(file_size=os.path.getsize(filename)))
    except Exception as e:
        print(f'upload error: {e}')
    else:
        print('upload successfully!')
    finally:
        ftps.close()


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        do(sys.argv[1])
    else:
        print('specify a protocol [mqtt]')
