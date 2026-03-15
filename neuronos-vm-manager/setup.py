"""
NeuronOS VM Manager
"""

from setuptools import setup, find_packages

setup(
    name="neuronos-vm-manager",
    version="0.1.0",
    description="NeuronOS VM Manager - Seamless Windows application integration",
    author="NeuronOS Project",
    author_email="dev@neuronos.org",
    url="https://github.com/neuronos/neuronos-vm-manager",
    packages=find_packages(),
    package_data={
        "neuronvm": ["../data/*.yaml"],
    },
    include_package_data=True,
    install_requires=[
        "PyYAML>=6.0",
        "libvirt-python>=9.0.0",
    ],
    extras_require={
        "gui": [
            "PySide6>=6.5.0",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "mypy>=1.0",
        ],
        "monitor": [
            "inotify-simple>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "neuronvm=neuronvm.cli:main",
            "neuronvm-launch=neuronvm.launcher:main",
        ],
        "gui_scripts": [
            "neuronvm-manager=neuronvm.ui.main:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Operating System",
    ],
)
