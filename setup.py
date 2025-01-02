from setuptools import setup, find_packages
from pathlib import Path
import re


here = Path(__file__).resolve().parent
README = (here / "README.rst").read_text(encoding="utf-8")

VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"

excluded_packages = ["docs", "tests", "tests.*"]

version_path = "mockpipe/_version.py"
verstrline = open(version_path, "rt").read()
res = re.search(VSRE, verstrline, re.M)

if res:
    version_string = res.group(1)
else:
    raise RuntimeError(f"Unable to find version string in {version_path}")

setup(
    name="mockpipe",
    version=version_string,
    description="Dummy data generator focusing on customisability and maintained relationships for mocking data pipelines",
    long_description=README,
    packages=find_packages(exclude=excluded_packages),
    install_requires=[
        "black==24.10.0",
        "click==8.1.7",
        "duckdb==1.0.0",
        "Faker==26.0.0",
        "faker-commerce==1.0.4",
        "pytest==8.3.2",
        "pytest-cov==5.0.0",
        "PyYAML==6.0.1",
    ],
    entry_points={
        "console_scripts": [
            "mockpipe=mockpipe.__main__:mockpipe_cli",
        ],
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
        "Topic :: Utilities",
    ],
    keywords="mocking data faker testing generator pipeline pipe",
    author="BenskiBoy",
    project_urls={
        "Source": "https://github.com/BenskiBoy/mockpipe",
        "Bug Tracker": "https://github.com/BenskiBoy/mockpipe/issues",
        "Changes": "https://github.com/BenskiBoy/mockpipe/blob/master/CHANGELOG.md",
    },
    python_requires=">=3.8",
)
