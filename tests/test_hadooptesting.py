import unittest
import testing.hadoop


class TestPostgresql(unittest.TestCase):
    def test_basic(self):
        # start hadoop-test server
        server = testing.hadoop.HadoopServer(hadoop_unit_path='/usr/local/hadoop-unit')

        try:
            self.assertIs(server.are_enabled_servers_started(), True)
            server.stop()
            self.assertIs(server.are_enabled_servers_started(), False)
        finally:
            server.stop()
