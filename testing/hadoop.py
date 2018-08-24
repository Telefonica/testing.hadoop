# -*- coding: utf-8 -*-
#  Copyright 2018 Jordi Sesmero
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import errno
import sys
from time import sleep

import os
import signal
import socket
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime

from .helpers import get_path_of, modify_conf_properties

__all__ = ['HadoopServer']


class HadoopServer(object):
    VALID_SERVERS = ['hdfs', 'zookeeper', 'alluxio', 'hivemeta', 'hiveserver2', 'kafka', 'hbase', 'solrcloud',
                     'oozie', 'mongodb', 'cassandra', 'elasticsearch', 'neo4j', 'knox', 'redis', 'yarn',
                     'confluent_kafka_rest', 'confluent_schemaregistry', 'confluent_kafka', 'confluent_ksql_rest']

    DEFAULT_SETTINGS = {
        'base_dir': '/tmp', 'hadoop_unit_path': '/usr/local/hadoop-unit',
        'enabled_servers': ['hdfs'],
        'hadoop_unit_default_props': {'hdfs.test.file': '/tmp/testing', 'maven.local.repo': '/tmp/m2',},
        'boot_timeout': 240,
        'stop_timeout': 120,
    }

    def __init__(self, **kwargs):
        self.name = self.__class__.__name__
        self.settings = deepcopy(self.DEFAULT_SETTINGS)
        self.settings.update(kwargs)
        self.child_process = None
        self._owner_pid = os.getpid()
        self._use_tmpdir = False
        self.hadoop_unit_props = {}
        self.hadoop_props = {}
        self.logger = None

        if os.name == 'nt':
            self.terminate_signal = signal.CTRL_BREAK_EVENT

        self.base_dir = self.settings.pop('base_dir')
        if self.base_dir:
            if self.base_dir[0] != '/':
                self.base_dir = os.path.join(os.getcwd(), self.base_dir)
        else:
            self.base_dir = tempfile.mkdtemp()
            self._use_tmpdir = True

        self.hadoop_unit_standalone = find_program('hadoop-unit-standalone', ['bin'],
                                                   base_dir=self.settings['hadoop_unit_path'])

        try:
            self.start()
        except Exception:
            self.cleanup()
            raise

    def __getattr__(self, name):
        return self.settings[name]

    def start(self):
        if self.child_process:
            return  # already started
        self.prestart()

        self.logger = open(os.path.join(self.base_dir, '%s.log' % self.name), 'wt')
        try:
            command = self.get_server_commandline()
            flags = 0
            if os.name == 'nt':
                flags |= subprocess.CREATE_NEW_PROCESS_GROUP
            self.child_process = subprocess.Popen(command, stdout=self.logger, stderr=self.logger,
                                                  creationflags=flags)
        except Exception as exc:
            raise RuntimeError('failed to launch %s: %r' % (self.name, exc))
        else:
            try:
                self.wait_booting()

                self.poststart()
            except Exception:
                self.stop()
                raise
        finally:
            self.logger.close()

    def stop(self, _signal=signal.SIGTERM):
        try:
            self.terminate(_signal)
        finally:
            self.cleanup()

    def terminate(self, _signal=None):
        if self.child_process is None:
            return  # not started

        if self._owner_pid != os.getpid():
            return  # could not stop in child process

        if _signal is None:
            _signal = self.terminate_signal

        try:
            command = self.get_server_commandline('stop')
            stop_child_process = subprocess.Popen(command)

            # block until stopped
            stop_child_process.communicate()

            killed_at = datetime.now()
            while self._pid_exists():
                if (datetime.now() - killed_at).seconds > self.settings.get('stop_timeout', 120):
                    self.child_process.kill()
                    stop_child_process.kill()
                    raise RuntimeError("*** failed to shutdown process (timeout) ***\n" + self.read_bootlog())

                sleep(0.1)

        except OSError:
            pass

        self.child_process = None

    def read_bootlog(self):
        try:
            with open(os.path.join(self.base_dir, '%s.log' % self.name)) as log:
                return log.read()
        except Exception as exc:
            raise RuntimeError("failed to open file:%s.log: %r" % (self.name, exc))

    def cleanup(self):
        # shall we cleanup hdfs artifacts?
        pass

    def wait_booting(self):
        boot_timeout = self.settings.get('boot_timeout')
        exec_at = datetime.now()
        while True:
            self.logger.flush()

            if self.child_process.poll() is not None:
                raise RuntimeError("*** failed to launch %s ***\n" % self.name +
                                   self.read_bootlog())

            if self.are_enabled_servers_listening() and self.are_enabled_servers_started():
                print("Server started...")
                break

            if (datetime.now() - exec_at).seconds > boot_timeout:
                raise RuntimeError("*** failed to launch %s (timeout) ***\n" % self.name +
                                   self.read_bootlog())

            sleep(0.1)

    def is_alive(self):
        return self.child_process and self.child_process.poll() is None

    def get_server_commandline(self, param='console'):
        return [self.hadoop_unit_standalone, param]

    def _is_hdfs_ready(self):
        from six.moves import urllib

        webhdfs_port = self.hadoop_unit_props['hdfs.namenode.http.port']
        url = 'http://localhost:{}/jmx?qry=Hadoop:service=NameNode,name=NameNodeStatus'.format(webhdfs_port)

        try:
            result = urllib.request.urlopen(url)
            content = result.read()
            server_active = content and b'"State" : "active"' in content

        except urllib.error.URLError as e:
            server_active = False

        return server_active

    def are_enabled_servers_started(self):
        """
        Does a JMX request to really determine server is UP and RUNNING
        :return:
        """
        CHECKERS = {
            'hdfs': self._is_hdfs_ready
            # implement here more health checks
        }

        enabled_servers = self.settings.get('enabled_servers', [])
        for server in enabled_servers:
            availability_checker = CHECKERS.get(server)
            if not availability_checker():
                return False

        return True

    def are_enabled_servers_listening(self):
        """
        Checks wether configured servers are listening in expected ports
        WARNING: Listening does not mean ready to accept requests
        :return:
        """
        enabled_servers = self.settings.get('enabled_servers', [])
        for server in enabled_servers:
            server_port = int(self._find_port(server))
            if server_port and not self._port_in_use(server_port):
                return False
        return True

    def _find_port(self, server):
        for key, value in self.hadoop_unit_props.items():
            if server in key and '.port' in key:
                return value
        return None

    def _pid_exists(self):
        return os.path.exists(os.path.join(self.settings['hadoop_unit_path'], 'logs', 'hadoop-unit-standalone.pid'))

    def prestart(self):
        """
        checks expected ports are not in use
        :return:
        """
        if self._pid_exists():
            raise Exception("Another server is already running, please kill it and delete hadoop-unit-standalone.pid")

        properties_path = os.path.join(self.settings['hadoop_unit_path'], 'conf')

        # modify custom properties from hadoop-unit
        self.hadoop_unit_props = modify_conf_properties(os.path.join(properties_path, 'hadoop-unit-default.properties'),
                               self.settings['hadoop_unit_default_props'])

        # enable or disable servers based on configuration
        self.hadoop_props = modify_conf_properties(os.path.join(properties_path, 'hadoop.properties'),
                                                        self._enabled_servers_properties())

    def _enabled_servers_properties(self):
        result = {}
        for server in self.VALID_SERVERS:
            result[server] = 'true' if server in self.settings['enabled_servers'] else 'false'
        return result

    def poststart(self):
        pass

    def _port_in_use(self, port_number):
        """
        Tries to bind to port, if it is denied it means server is running
        :param port_number:
        :return:
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.bind(("127.0.0.1", port_number))
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                return True
        finally:
            s.close()

        return False

    def __del__(self):
        try:
            self.stop()
        except Exception:
            errmsg = ('ERROR: testing.hadoop: failed to shutdown the server automatically.\n'
                      'Any server processes and files might have been leaked. Please remove them and '
                      'call the stop() certainly')
            try:
                sys.__stderr__.write(errmsg)
            except Exception:
                # if sys module is already unloaded by GC
                print(errmsg)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()


def find_program(name, subdirs, base_dir):
    path = get_path_of(name)
    if path:
        return path

    for subdir in subdirs:
        path = os.path.join(base_dir, subdir, name)
        if os.path.exists(path):
            return path
