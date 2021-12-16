from __future__ import (absolute_import, division, print_function)

from io import StringIO
import requests, json
__metaclass__ = type

import ansible.constants as C
from ansible.errors import AnsibleError, AnsibleConnectionFailure
from ansible.module_utils.six import text_type, binary_type
from ansible.module_utils._text import to_bytes, to_native, to_text
from ansible.plugins.connection import ConnectionBase
from ansible.utils.display import Display

display = Display()


# 编写插件就是继承 ConnectionBase 类，然后实现父类的几个方法

# 这个是类的继承
class Connection(ConnectionBase):
    ''' Local based connections '''

    #定义私有属性,私有属性在类外部无法直接进行访问
    __weight = 0


    transport = 'local'
    has_pipelining = True

    # 类有一个名为 __init__() 的特殊方法（构造方法），该方法在类实例化时会自动调用
    def __init__(self, *args, **kwargs):
        # super 使用子类对象调用父类已经被覆盖的方法
        # 加了星号 * 的参数会以元组(tuple)的形式导入
        # 加了两个星号 ** 的参数会以字典的形式导入
        super(Connection, self).__init__(*args, **kwargs)
        self.cwd = None

    # 类的方法与普通方法有个区别，他必须接受第一个参数，惯例为 self
    # self 代表类的实例，而不是类
    def _connect(self):
        ''' connect to the local host; nothing to do here '''
        return self

    #
    # Main public methods 插件执行核心方法
    #
    def exec_command(self, cmd, in_data=None, sudoable=True):
        addr = self._play_context.remote_addr
        if isinstance(cmd, (text_type, binary_type)):
            cmd = to_bytes(cmd)
        else:
            cmd = map(to_bytes, cmd)

        files = {}
        if in_data:
            files['stdin'] = StringIO(in_data)

        resp = requests.post('http://{}:8700/exec'.format(addr), data={'command': cmd}, files=files)
        if not resp.ok:
            raise AnsibleConnectionFailure('Failed to exec command on {}: {}'.format(addr, resp.reason))

        data = resp.json()
        return data['status'], data['stdout'], data['stderr']

    def put_file(self, in_path, out_path):
        # with 的作用就是自动调用close（）方法
        with open(in_path) as fp:
            remote_addr = self._play_context.remote_addr
            resp = requests.put('http://{}:8700/upload'.format(remote_addr), data={'dest': out_path}, files={'src': fp})

            if not resp.ok:
                raise AnsibleConnectionFailure('Failed to upload file: {}'.format(resp.reason))

    def fetch_file(self, in_path, out_path):
        ''' fetch a file from local to local -- for compatibility '''
        super(Connection, self).fetch_file(in_path, out_path)

        display.vvv(u"FETCH {0} TO {1}".format(in_path, out_path), host=self._play_context.remote_addr)
        self.put_file(in_path, out_path)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        self._connected = False

    def fetch_file(self, in_path, out_path):
        raise AnsibleError("not unimplemented")

    def close(self):
        pass
