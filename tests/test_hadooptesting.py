import unittest
import testing.hadoop


class TestPostgresql(unittest.TestCase):
    def test_basic(self):
        # start hadoop-test server
        server = testing.hadoop.HadoopServer(hadoop_unit_path='/usr/local/hadoop-unit')

        try:
            self.assertIs(server.is_server_available(), True)
            server.stop()
            self.assertIs(server.is_server_available(), False)
        finally:
            server.stop()
