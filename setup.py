from setuptools import setup, find_packages


setup(
    name="Paper2Post",
    version="0.1.0",
    description="Generate multi-platform posts from a paper PDF.",
    packages=find_packages(),
    install_requires=[
        "pypdf>=5.0.0",
        "httpx>=0.27.0",
    ],
    entry_points={
        "console_scripts": [
            "papercaster=Paper2Post.cli:main",
        ]
    },
)

