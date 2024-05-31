# File: setup.py
# Date: 6-Oct-2018
#
# Update:
#
import re

from setuptools import find_packages
from setuptools import setup

packages = []
thisPackage = 'wwpdb.apps.releasemodule'

with open('wwpdb/apps/releasemodule/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')


setup(
    name=thisPackage,
    version=version,
    description='wwPDB sequence module',
    long_description="See:  README.md",
    author='Ezra Peisach',
    author_email='ezra.peisach@rcsb.org',
    url='https://github.com/rcsb/py-wwpdb_apps_releasemodule',
    #
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        # 'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    #
    install_requires=['mmcif', 'wwpdb.apps.msgmodule', 'wwpdb.apps.wf_engine',
                      'wwpdb.io', 'wwpdb.utils.config >= 0.24',
                      'wwpdb.utils.dp ~= 0.48',
                      'wwpdb.utils.emdb ~= 1.0', 'wwpdb.utils.session',
                      'wwpdb.utils.wf', 'mmcif.utils', 'wwpdb.utils.db >= 0.8',
                      'rcsb.utils.multiproc'],
    packages=find_packages(exclude=['wwpdb.apps.tests-releasemodule',
                                    'mock-data']),
    # Enables Manifest to be used
    # include_package_data = True,
    package_data={
        # If any package contains *.md or *.rst ...  files, include them:
        '': ['*.md', '*.rst', "*.txt", "*.cfg"],
    },
    #
    # These basic tests require no database services -
    test_suite="wwpdb.apps.tests-releasemodule",
    tests_require=['tox'],
    #
    # Not configured ...
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
    # Added for
    command_options={
        'build_sphinx': {
            'project': ('setup.py', thisPackage),
            'version': ('setup.py', version),
            'release': ('setup.py', version)
        }
    },
    # This setting for namespace package support -
    zip_safe=False,
)
