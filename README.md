# testing.hadoop
Objective: bring https://github.com/jetoile/hadoop-unit into python so Integration tests are possible.

# Prerequisites
Follow these steps: 

* Download it from [search.maven.org](https://search.maven.org/remotecontent?filepath=fr/jetoile/hadoop/hadoop-unit-standalone/2.8/hadoop-unit-standalone-2.8.tar.gz)
* Unzip it (default path is /usr/local/hadoop-unit)
* hadoop.properties and hadoop-unit-default.properties are modified *automatically*.




And test it manually: `$ bin/hadoop-unit-standalone console`
```
jvm 1    | 12:13:41.550 INFO  HdfsBootstrap:167 - fr.jetoile.hadoopunit.component.HdfsBootstrap is started
jvm 1    | 		 - HDFS
jvm 1    |  			 host:localhost
jvm 1    |  			 port:20112
```



# Usage
```
import testing.hadoop
with testing.hadoop.Server(hadoop_unit_path='/usr/local/hadoop-unit') as server:
    hdfs_port = server.hadoop_unit_props['hdfs.namenode.port']
    webhdfs_port = server.hadoop_unit_props['hdfs.namenode.http.port']

```


# But I just want hdfs!
It's the only enabled by default server, so you are fine.

# But I want more than hdfs!
Just pass enabled_servers to Server with a list of one of the supported servers (defined in Server.VALID_SERVERS)
```
enabled_servers=['hdfs', 'zookeeper']
```

Also you could modify any of the properties passing a dictionary to:
```
hadoop_unit_default_props={'hdfs.test.file': '/tmp/testing', 'maven.local.repo': '/tmp/m2',}
```

# Caveats
It's hard to determine when server is started properly

# Contributing
Use the GitHub's pull request and issue tracker to provide patches or report problems with the library. All new functionality must be covered by unit tests before it can be included in the repository.

The master branch always has the cutting edge version of the code, if you are using it in your project it would be wise to create a fork of the repository or target a specific tag/commit for your dependencies.
