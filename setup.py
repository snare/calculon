from setuptools import setup

setup(
    name = "calculon",
    version = "0.1",
    author = "snare",
    author_email = "snare@ho.ax",
    description = ("A terminal-based programmer's calculator endowed with unholy acting talent by the Robot Devil"),
    license = "Buy snare a beer",
    keywords = "calculator programmer hex 64-bit",
    url = "https://github.com/snarez/calculon",
    packages=['calculon'],
    install_requires = ['bpython'],
    entry_points = {
        'console_scripts': ['calculon = calculon:main']
    }
)
