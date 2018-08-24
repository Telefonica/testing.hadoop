# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.2",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Topic :: Hadoop",
    "Topic :: Software Development",
    "Topic :: Software Development :: Testing",
]

install_requires = ['javaproperties', 'six']
if sys.version_info < (2, 7):
    install_requires.append('unittest2')


setup(
    name='testing.hadoop',
    version='0.0.1',
    description='automatically launches a hadoop standalone testing server',
    long_description=open('README.md').read(),
    classifiers=classifiers,
    keywords=[],
    author='Jordi Sesmero',
    url='https://github.com/jsmolina/testing.hadoop',
    license='Apache License 2.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    tests_require=install_requires + ['nose'],
    test_suite="nose.collector",
    extras_require=dict(
        testing=[
            'nose',
        ],
    ),
)