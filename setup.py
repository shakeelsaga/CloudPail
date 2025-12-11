from setuptools import setup, find_packages

setup(
    name="cloudpail",
    version="1.0.0",
    description="The Developer-First CLI for AWS S3 Management",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="shakeelsaga",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "boto3",
        "rich",
        "InquirerPy",
        "pyperclip"
    ],
    entry_points={
        "console_scripts": [
            "cloudpail=cloudpail.main:main",
        ],
    },
)