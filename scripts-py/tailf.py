# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
from typing import List


def must_print_lines(lines: List[str]):
    for line in lines:
        try:
            print(line.decode(), end='')
        except UnicodeDecodeError:
            print(line)


def tailf(filepath: str):
    last_stat = None

    while True:
        stat = os.stat(filepath)

        if last_stat is None:
            with open(filepath, 'rb') as f:
                byte_num = 1024
                while True:
                    if stat.st_size <= byte_num:
                        tail = f.readlines()
                        if len(tail) > 10:
                            tail = tail[-10:]
                        break
                    else:
                        f.seek(-byte_num, 2)
                        tail = f.readlines()
                        if len(tail) > 10:
                            tail = tail[-10:]
                            break
                        byte_num *= 2
            must_print_lines(tail)
            last_stat = stat
        elif stat.st_mtime_ns != last_stat.st_mtime_ns:
            # 只有文件变大的时候才会读取并打印
            if stat.st_size > last_stat.st_size:
                with open(filepath, 'rb') as f:
                    f.seek(last_stat.st_size, 0)
                    tail = f.readlines()
                must_print_lines(tail)
            last_stat = stat

        time.sleep(0.1)


def exit_handler(sig_num, frame):
    print("停止读取...")
    sys.exit()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    if len(sys.argv) < 2:
        print('请输入文件名...')
        sys.exit(-1)

    filename = sys.argv[1]
    tailf(os.path.abspath(filename))
