#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

try:
    import multiprocessing  # noqa
except:
    pass


VERSION = '0.1.1'


setup(
    name='spielbash',
    version=VERSION,
    author="Software Factory team.",
    author_email="softwarefactory@redhat.com",
    description="an automator for asciinema bash movies",
    packages=find_packages(exclude=['ez_setup']),
    test_suite='nose.collector',
    url="http://softwarefactory-project.io/r/gitweb?p=spielbash.git",
    license="Apache v2.0",
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Distributed Computing"
    ],
    entry_points={
        "console_scripts": [
            'spielbash = spielbash:main'],
    },
    include_package_data=True,
)
