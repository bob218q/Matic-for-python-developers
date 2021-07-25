import re
import os.path
import sys
import platform
from setuptools import setup, find_packages

PY_VER = sys.version_info
if PY_VER < (3, 5):
    raise RuntimeError("aioredis doesn't support Python version prior 3.5")
#
# with open('requirements.txt') as f:
#     install_requires = [line for line in f]

install_requires = [
    'eth_abi == 2.0.0',
    'eth_account == 0.4.0',
    'eth_utils == 1.9.0',
    'requests == 2.22.0',
    'tenacity == 6.1.0',
    'tornado == 6.0.4',
    "solidity_parser",
    "antlr4-python3-runtime>=4.7,<4.8"
]

classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 4 - Beta',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3 :: Only',
    'Operating System :: POSIX',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries'
]

setup(name='maticvigil-sdk',
      version='0.1.a.dev',
      description="Python SDK for MaticVigil (Matic.Network) APIs",
      # long_description="\n\n".join((read('README.rst'), read('CHANGES.txt'))),
      classifiers=classifiers,
      platforms=["POSIX"],
      author="BlockVigil Inc",
      author_email="hello@blockvigil.com",
      url="https://maticvigil.com/docs",
      license="MIT",
      packages=['maticvigil'],
      install_requires=install_requires,
      include_package_data=True
      )
