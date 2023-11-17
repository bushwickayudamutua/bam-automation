import os
from setuptools import setup, find_packages

reqs = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "requirements.txt")
)
with open(reqs) as f:
    install_requires = [req.strip().split("==")[0] for req in f]

config = {
    "name": "bam-app",
    "version": "0.0.1",
    "packages": find_packages(),
    "install_requires": install_requires,
    "author": "BAM",
    "author_email": "bushwickayudamutua@gmail.com",
    "description": "API and Interface for BAM Automations",
    "url": "http://bushwickayudamutua.org",
}

setup(**config)
