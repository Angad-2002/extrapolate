"""Setup script for GCP FinOps Dashboard."""

from setuptools import setup, find_packages

setup(
    name="xpol",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
)

