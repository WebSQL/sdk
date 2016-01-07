#!/usr/bin/env python

from setuptools import setup

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
    with open('README') as r:
        return r.read()


setup(
    name="wsql_sdk",
    version="0.3.9",
    description='The chain of tools, that to make work with SQL easier',
    packages=["wsql_sdk", "wsql_sdk._lang"],
    requires=["pyparsing"],
    author="Bulat Gaifullin",
    author_email='gaifullinbf@gmail.com',
    maintainer='Bulat Gaifullin',
    maintainer_email='gaifullinbf@gmail.com',
    url='https://github.com/WebSQL/sdk',
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
            'wsql-codegen=wsql_sdk.codegen:main',
            'wsql-trans=wsql_sdk.translator:main',
        ],
    }
)
