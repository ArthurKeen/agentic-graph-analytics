"""
Setup script for Graph Analytics AI library.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="graph-analytics-ai",
    version="3.0.0",
    description="AI-assisted graph analytics platform with automated workflow orchestration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Arthur Keen",
    author_email="",
    url="https://github.com/ArthurKeen/graph-analytics-ai",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "python-arango>=7.0.0",
        "requests>=2.28.0",
        "python-dotenv>=0.19.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "mcp": [
            "mcp[cli]>=1.0.0",
        ],
        "api": [
            "fastapi>=0.110.0",
            "uvicorn[standard]>=0.27.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "gaai=graph_analytics_ai.ai.cli:main",
            "gaai-mcp=graph_analytics_ai.mcp.server:main",
            "gaai-product-api=graph_analytics_ai.product.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries",
    ],
    keywords="arangodb graph analytics gae orchestration ai llm automation workflow",
)

