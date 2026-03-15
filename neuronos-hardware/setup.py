"""
NeuronOS Hardware Detection System
"""

from setuptools import setup, find_packages

setup(
    name="neuron-hw",
    version="0.1.0",
    description="NeuronOS Hardware Detection and VFIO Configuration System",
    author="NeuronOS Project",
    author_email="dev@neuronos.org",
    url="https://github.com/neuronos/neuronos-hardware",
    packages=find_packages(),
    package_data={
        "neuron_hw": ["../data/*.yaml"],
    },
    include_package_data=True,
    install_requires=[
        "PyYAML>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "neuron-hwdetect=neuron_hw.cli:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Hardware",
    ],
)
