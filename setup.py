#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import unicode_literals, print_function, division

from gredis import version

from setuptools import setup

setup(
    name="gredis",
    version=version,
    packages=["gredis"],
    package_data={
    },
    author="cold",
    author_email="wh_linux@126.com",
    url="https://github.com/coldnight/gredis",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    description=("gRedis is an asynchronous client library of Redis written "
                 "with Tornado coroutine."),
    long_description=open("README.rst").read(),
    install_requires=["tornado>=4.0", "redis"],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        ],
)
