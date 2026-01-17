"""
Setup script for Multi-Agent RAG with DSPy
"""

from setuptools import setup, find_packages

with open("README_DSPY.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="multi-agent-rag-dspy",
    version="1.0.0",
    author="Your Team",
    author_email="your.email@example.com",
    description="Multi-Agent RAG System with Meta-Cognitive Reasoning using DSPy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-repo/multi-agent-rag-dspy",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: ISC License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "ipython>=8.0.0",
            "jupyter>=1.0.0"
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "multi-agent-rag=examples.medical_rag_example:main"
        ]
    }
)
