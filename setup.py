# coding: utf-8
import sys
from os.path import join, dirname
from setuptools import setup
from setuptools.command.test import test

import pycsob


def parse_reqs(f='requirements.pip'):
    ret = []
    with open(join(dirname(__file__), f)) as fp:
        for l in fp.readlines():
            l = l.strip()
            if l and not l.startswith('#'):
                ret.append(l)
    return ret


setup_requires = ['setuptools']
install_requires, tests_require = parse_reqs(), parse_reqs('requirements-test.pip')


with open('README.rst') as readmefile:
    long_description = readmefile.read()


class PyTest(test):
    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='pycsob',
    version=pycsob.__versionstr__,
    description='Python client for ČSOB Payment Gateway',
    long_description=long_description,
    author='Twisto',
    author_email='devs@twisto.cz',
    license='MIT',
    url='https://github.com/TwistoPayments/pycsob',

    packages=['pycsob', 'tests_pycsob'],
    include_package_data=True,

    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
    ],
    zip_safe=False,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    cmdclass={'test': PyTest}
)
