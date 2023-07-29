from setuptools import setup, find_namespace_packages

setup(
    name='thingwala-geyserwala',
    description="Python bindings to the Geyserwala REST API",
    author="Thingwala",
    url="https://github.com/thingwala/geyserwala-py",
    license="MIT",
    packages=find_namespace_packages(include=['thingwala.*']),
    version=open('version', 'rt', encoding="utf8").read().strip(),
    install_requires=open('requirements.txt', encoding="utf8").readlines(),
    tests_require=open('requirements_dev.txt', encoding="utf8").readlines(),
    entry_points={
        "console_scripts": [
            "geyserwala=thingwala.geyserwala.aio.cli:cli",
        ]
    },
)
