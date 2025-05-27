from setuptools import setup, find_packages

setup(
    name="girlfriend-call",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "PyQt5>=5.15.0",
        "PyAudio>=0.2.13",
        "numpy>=1.21.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "girlfriend-call=main:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A free cross-platform audio calling application",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="audio, voip, p2p, calling",
    url="https://github.com/yourusername/girlfriend-call",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Communications :: Internet Phone",
    ],
)
