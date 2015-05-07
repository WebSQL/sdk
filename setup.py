#!/usr/bin/env python

from setuptools import setup
import os

try:
    from sphinx.setup_command import BuildDoc as _BuildDoc

    class BuildDoc(_BuildDoc):
        def finalize_options(self):
            super().finalize_options()
            if not self.project:
                self.project = self.distribution.name
            if not self.version:
                self.version = self.distribution.version

except ImportError:
    BuildDoc = None


def readme():
    with open(os.path.join('README')) as r:
        return r.read()


setup(
    name="sqltoolchain",
    version="0.0.3",
    description='The toolchain to make work with SQL easier',
    packages=["sqltoolchain", "sqltoolchain.syntax"],
    requires=["pyparsing"],
    author="@bg",
    author_email='gaifullinbf@gmail.com',
    maintainer='@bg',
    maintainer_email='gaifullinbf@gmail.com',
    url='https://github.com/WebSQL/sqltoolchain',
    license='MIT',
    long_description=readme(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Database",
        "Topic :: Database :: Database Engines/Servers",
    ],
    entry_points={
        'console_scripts': [
            'sql-pygen=sqltoolchain.pygen:main',
            'sql-preprocessor=sqltoolchain.preprocessor:main',
        ],
    }
)
