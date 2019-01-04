import pathlib
from setuptools import setup,find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()

setup(
    name="py2snes",
    version="0.3.0",
    author="Thomas Prescott",
    author_email="tcprescott@gmail.com",
    description="A python module for interacting with the sd2snes using the usb2snes firmware by Redguyyyy.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/tcprescott/py2snes",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires=['websocket-client'],
)