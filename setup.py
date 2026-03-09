"""
打包配置文件
"""

from setuptools import setup, find_packages

setup(
    name="CRTicketMonitor",
    version="2.2.0",
    description="12306余票监控工具",
    author="BH7GUL",
    author_email="",
    url="",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests>=2.25.0",
        "prettytable>=2.0.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "crticket=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
