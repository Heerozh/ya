"""Setup configuration for ya benchmark framework."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ya",
    version="0.1.0",
    author="Ya Team",
    description="A Python async benchmark framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "pandas>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ya=ya.cli:main",
        ],
    },
)
