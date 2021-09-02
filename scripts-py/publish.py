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
import socket
from typing import Sized


class ImplicitFTPS(ftplib.FTP_TLS):
    def connect(self, host: str, port: int = 990) -> str:
        if host:
            self.host = host
        if port > 0:
            self.port = port

        self.sock = socket.create_connection((self.host, self.port),
                                             self.timeout, self.source_address)
        self.sock = self.context.wrap_socket(self.sock)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding='utf-8')
        self.welcome = self.getresp()

        return self.welcome


def do(program: str) -> None:
    if program == 'mqtt':
        os.chdir('../code/mqtt_prot_server/src/mqtt_prot_server')
    elif program == 'tcp':
        os.chdir('../code/third_prot_server/src/third_prot_server')
    elif program == 'rtu':
        os.chdir('../code/third_rtulog_service/src/third_rtulog_service')
    else:
        print(f'unsupported program: {program}')

    os.putenv('GOOS', 'linux')
    os.putenv('GOARCH', 'amd64')
    bin_name = os.path.basename(os.getcwd())
    img_name = f'{bin_name}:latest'
    tar_name = f'{bin_name}.tar'

    print('start building ...')

    try:
        subprocess.check_call(f'go build -ldflags "-s -w" -o {bin_name}')
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
    def __init__(self, file_size=0) -> None:
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

    cb = ProgressIndicator(os.path.getsize(filename))
    try:
        ftps = ImplicitFTPS(user='dingdx@teld.local',
                            passwd='Deri!20170713',
                            host='ftp.teld.cn',
                            timeout=3)
        ftps.prot_p()
        ftps.cwd('/eys/huaweityun')
        with open(filename, 'rb') as f:
            ftps.storbinary(f'STOR {filename}', f, callback=cb)
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
        print('specify a program [mqtt tcp rtu]')
