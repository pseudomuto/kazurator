import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

installation_requirements = [
    "kazoo>=2.0.0"
]

test_requirements = installation_requirements + [
    "flake8>=3.2.1",
    "nose>=1.3.7",
    "pep8>=1.7.0",
    "tox>=2.3.1"
]

setup(
    name="kazurator",
    author="David Muto (pseudomuto)",
    author_email="david.muto@gmail.com",
    version="0.1.1",
    description="Inter process lock recipes that play nice with curator",
    long_description=README,
    url="https://github.com/pseudomuto/kazurator",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Communications",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Networking",
    ],
    keywords="zookeeper lock",
    packages=find_packages(),
    install_requires=installation_requirements,
    tests_require=test_requirements,
    test_suite="kazurator.tests",
    extras_require={
        "test": test_requirements
    }
)
