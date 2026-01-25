#!/usr/bin/env python3
"""
Setup script for Hockey Editor Pro
"""

from setuptools import setup, find_packages
import os

# Read requirements
def read_requirements():
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read README
def read_readme():
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()

setup(
    name="hockey_editor_pro",
    version="2.0.0",
    description="Professional Video Analysis Tool for Hockey",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Hockey Editor Team",
    author_email="",
    url="https://github.com/mijeha4/hockey_editor",
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Image Processing",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'hockey-editor=main:main',
        ],
    },
    package_data={
        'hockey_editor': [
            'assets/**/*',
            'config.json',
        ],
    },
    data_files=[
        ('', ['config.json']),
    ],
    zip_safe=False,
)
