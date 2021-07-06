# -*- coding: utf-8 -*-
"""yea setup."""

from setuptools import setup


setup(
    name='yea',
    version='0.1',
    description="Test harness breaking the sound barrier",
    packages=[
        'yea'
    ],
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'yea=yea.cli:cli',
        ]
    },
    include_package_data=True,
    zip_safe=False,
    license="MIT license",
    python_requires='>=3.5',
)
