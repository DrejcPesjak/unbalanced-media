from setuptools import find_packages, setup


setup(
    name="eventregistry-llm",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"console_scripts": ["eventregistry-llm=eventregistry_llm.cli:main"]},
)
