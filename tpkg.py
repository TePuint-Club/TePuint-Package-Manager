# encoding:utf-8
import argparse
import json
import os
import sqlite3
import subprocess
import sys
from subprocess import PIPE

import requests


def cop(m, t):
    if m == 'info':
        rt = '\033[0;34m[info]\033[0m %s' % (t)
    elif m == 'warning':
        rt = '\033[0;33m[warning]\033[0m %s' % (t)
    elif m == 'error':
        rt = '\033[0;31m[error]\033[0m %s' % (t)
    return rt


def cmd_run(cmd):
    r = subprocess.run(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=True)
    return r.returncode


def api_req(url, name, ec):
    api = requests.get('%s%s' % (url, name))
    if api.status_code == 200:
        if api.text == 'error':
            print(cop('error', ec))
            sys.exit(1)
        return api.text


if cmd_run('ping -n 1 api.rainapi.cn'):
    print('无法连接到服务器')
    sys.exit(1)
os.system('')
os.chdir(os.path.dirname(__file__))
os.environ['path'] = "%s%s%s" % (
    os.getenv('path'), os.path.dirname(os.path.abspath(__file__)), '\\bin')
os.environ['pdir'] = "%s%s" % (os.path.dirname(
    os.path.abspath(__file__)), '\\programs\\')
os.environ['pthd'] = "%s%s" % (os.path.dirname(
    os.path.abspath(__file__)), '\\path\\')

conn = sqlite3.connect('list.db')
c = conn.cursor()


def prog_check(prog):
    cur = c.execute('SELECT * FROM "main"."packages" WHERE "name" = \'%s\'' %
                    (prog))
    check = cur.fetchone()
    if check is not None:
        return True
    return False


def install(prog):
    print(cop('info', '正在安装 %s' % (prog)))
    prog_info = json.loads(
        api_req('https://api.rainapi.cn/tpm/?o=info&v=', prog, '错误的软件包名称'))
    print(cop('info', '软件包定位成功'))
    if prog_check(prog_info['name']):
        sr = input(cop('warning', '软件包已存在，是否卸载后安装(y/n)'))
        if sr.lower() == 'y' or sr.lower() == 'yes':
            remove(prog)
        elif sr.lower() == 'n' or sr.lower() == 'no':
            print(cop('error', '用户取消操作'))
            sys.exit(2)
        else:
            print(cop('error', '错误输入'))
            sys.exit(3)
    if cmd_run('git clone %s ./programs/%s' %
               (prog_info['url'], prog_info['name'])):
        print(cop('error', '下载失败'))
        sys.exit(1)
    print(cop('info', '下载成功，执行安装脚本'))
    for cmd in prog_info['install'].split('\r\n'):
        cmd_run(cmd)
    print(cop('info', '脚本执行完毕'))
    c.execute(
        'INSERT INTO "main"."packages" ("name", "version") VALUES (\'%s\', \'%s\')'
        % (prog_info['name'], prog_info['version']))
    conn.commit()
    print(cop('info', '安装完成'))


def remove(prog):
    print(cop('info', '正在卸载 %s' % (prog)))
    rm_info = json.loads(
        api_req('https://api.rainapi.cn/tpm/?o=remove&v=', prog, '错误的软件包名称'))
    if not prog_check(rm_info['name']):
        print(cop('error', '软件包不存在'))
        sys.exit(3)
    print(cop('info', '软件包定位成功，正在卸载'))
    cmd_run('rd /s/q programs\\%s' % (rm_info['name']))
    for cmd in rm_info['remove'].split('\r\n'):
        cmd_run(cmd)
    c.execute('DELETE FROM "main"."packages" WHERE  "name" = \'%s\'' %
              (rm_info['name']))
    conn.commit()
    print(cop('info', '卸载完成'))


def update(prog):
    up_info = json.loads(
        api_req('https://api.rainapi.cn/tpm/?o=info&v=', prog, '错误的软件包名称'))
    if not prog_check(up_info['name']):
        print(cop('error', '软件包不存在'))
        sys.exit(3)
    cur = c.execute(
        'SELECT "version" FROM "main"."packages" WHERE "name" = \'%s\'' %
        (up_info['name']))
    webver = cur.fetchone()
    if webver[0] < up_info['version']:
        remove(up_info['name'])
        install(up_info['name'])
    else:
        print(cop('info', '%s 无需升级' % (up_info['name'])))


parser = argparse.ArgumentParser()
parser = argparse.ArgumentParser(description='TePuint Club软件包管理器',
                                 prog='TePuint Package Manager')
command = parser.add_mutually_exclusive_group()
command.add_argument('--install', '-i', nargs='*', help='安装软件包')
command.add_argument('--remove', '-r', nargs='*', help='卸载软件包')
command.add_argument('--upgrade', help='更新软件包(指定)')
command.add_argument('--update',
                     '-u',
                     action='store_true',
                     default=False,
                     help='更新软件包(全部)')
command.add_argument('--list',
                     '-l',
                     action='store_true',
                     default=False,
                     help='显示已安装软件包列表')
command.add_argument('--version',
                     '-v',
                     action='version',
                     version='%(prog)s 1.0',
                     help='查看管理器版本')
command.add_argument('--search', '-s', help='搜索软件包(仅显示前10条,目前不支持正则)')
result = parser.parse_args()

if result.install is not None:
    for prog_name in result.install:
        install(prog_name)
        req = api_req('https://api.rainapi.cn/tpm/?o=req&v=',
                      '%s' % (prog_name), '依赖查询失败')
        if not req == 'none':
            req_list = req.split('\r\n')
            for reqs in req_list:
                install(reqs)
    conn.close()
    sys.exit(0)

if result.remove is not None:
    for prog_name in result.remove:
        remove(prog_name)
    conn.close()
    sys.exit(0)

if result.upgrade is not None:
    update(result.upgrade)
    sys.exit(0)

if result.update is True:
    cur = c.execute('SELECT "name" FROM "main"."packages"')
    prog_list = cur.fetchone()
    for prog in prog_list:
        update(prog)
    sys.exit(0)

if result.search is not None:
    res = json.loads(
        api_req('https://api.rainapi.cn/tpm/?o=search&v=', result.search,
                '未找到软件包'))
    for prog_info in res:
        print('名称：%s\t版本：%s\t作者：%s\t简介：%s' %
              (prog_info['name'], prog_info['version'], prog_info['auther'],
               prog_info['intro']))
    conn.close()
    sys.exit(0)

if result.list is True:
    cur = c.execute('SELECT * FROM "main"."packages"')
    for row in cur:
        print('名称：%s\t版本:%s' % (row[1], row[2]))
    conn.close()
    sys.exit(0)
