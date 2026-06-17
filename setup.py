# setup.py - تنظیمات پکیج

from setuptools import setup, find_packages

setup(
    name="config_manager",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "python-telegram-bot==22.7",
        "aiohttp==3.12.15",
        "aiosqlite==0.21.0",
        "SQLAlchemy==2.0.43",
        "pydantic-settings==2.10.1",
        "pydantic==2.11.7",
        "loguru==0.7.3",
        "APScheduler==3.11.0",
        "beautifulsoup4==4.14.3",
        "python-dotenv==1.2.2",
    ],
    python_requires=">=3.8",
    description="Automated V2Ray Config Collector, Validator & Publisher",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Config Manager Team",
    url="https://github.com/config-manager/config-manager",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
