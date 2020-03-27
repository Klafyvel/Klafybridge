from setuptools import setup, find_packages

setup(
    name="Klafybridge",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "klafybridge = klafybridge:main",
        ],
    },
    install_requires=open('requirements.txt').read(),
    # metadata to display on PyPI
    author="Hugo LEVY-FALK",
    author_email="hugo@klafyvel.me",
    description="This is a bridge between Telegram and IRC",
    long_description_content_type="text/markdown",
    #long_description=open('README.md').read(),
    keywords="telegram irc",
    url="http://github.com/Klafyvel/Klafybridge",   # project home page, if any
    project_urls={
        "Source Code": "http://github.com/Klafyvel/Klafybridge",
    },
    classifiers=[
        'License :: OSI Approved :: MIT License'
    ],
)
