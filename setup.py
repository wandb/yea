"""yea setup."""

from setuptools import setup


setup(
    name="yea",
    version="0.8.3",
    description="Test harness breaking the sound barrier",
    packages=["yea"],
    install_requires=[
        "coverage",
        "importlib-metadata>=3.0.0",
        "jsonschema",
        "junit-xml",
        "PyYAML",
        "requests",
        "typing_extensions",
    ],
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "yea=yea.cli:cli",
        ]
    },
    include_package_data=True,
    package_data={"": ["yea/schema-*.json"]},
    zip_safe=False,
    license="MIT license",
    python_requires=">=3.6",
)
