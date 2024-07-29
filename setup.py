import sys
from os.path import join, dirname
from setuptools import setup

import pycsob


def parse_reqs(f="requirements.pip"):
    ret = []
    with open(join(dirname(__file__), f)) as fp:
        for line in fp.readlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ret.append(line)
    return ret


setup_requires = ["setuptools"]
install_requires = parse_reqs()

with open("README.rst") as readme_file:
    long_description = readme_file.read()


setup(
    name="pycsob",
    version=pycsob.__versionstr__,
    description="Python client for ČSOB Payment Gateway",
    long_description=long_description,
    author="Twisto",
    author_email="devs@twisto.cz",
    license="MIT",
    url="https://github.com/TwistoPayments/pycsob",
    packages=["pycsob"],
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Utilities",
    ],
    zip_safe=False,
    setup_requires=setup_requires,
    install_requires=install_requires,
)
