from setuptools import find_packages, setup

with open("requirements.txt", encoding="utf-8") as f:
    install_requires = [line for line in f.read().splitlines() if line.strip()]

with open("README.md", encoding="utf-8") as f:
    readme = f.read()

setup(
    name="nepub",
    version="1.5.0",
    description="Small tool to convert Narou and Kakuyomu novels to vertically written EPUBs.",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="tama@ttk1.net",
    author_email="tama@ttk1.net",
    url="https://github.com/ttk1/nepub",
    license="MIT",
    python_requires=">=3.10",
    install_requires=install_requires,
    packages=find_packages(exclude=("test",)),
    package_data={"": ["files/*", "templates/*"]},
    entry_points={"console_scripts": ["nepub = nepub.__main__:main"]},
)
