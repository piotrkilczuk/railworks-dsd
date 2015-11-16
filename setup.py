#!/usr/bin/env python

import os
import setuptools


CLASSIFIERS = [
    'Development Status :: 1 - Planning',
    'Environment :: Win32 (MS Windows)',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: MIT License',
    'Operating System :: Microsoft :: Windows',
    'Programming Language :: Python',
    'Topic :: Games/Entertainment :: Simulation',
]


setuptools.setup(
    author='Piotr Kilczuk',
    author_email='piotr@tymaszweb.pl',
    name='railworks-dsd',
    version='0.0.1',
    description='Makes your USB footswitch work as driver viligance device in Train Simulator 2016',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    url='https://github.com/centralniak/railworks-dsd',
    license='MIT License',
    platforms=['Windows'],
    classifiers=CLASSIFIERS,
    entry_points={
        'console_scripts': [
            'railworksdsd = dsd:__main__'
        ]
    },
    install_requires=open('requirements.txt').read(),
    tests_require=open('test_requirements.txt').read(),
    packages=setuptools.find_packages(),
    include_package_data=False,
    zip_safe=False,
    test_suite='nose.collector',
)
