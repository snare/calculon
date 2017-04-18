from setuptools import setup

setup(
    name="calculon-calc",
    version="0.2",
    author="snare",
    author_email="snare@ho.ax",
    description=("A terminal-based programmer's calculator endowed with unholy acting talent by the Robot Devil"),
    license="Buy snare a beer",
    keywords="calculator programmer hex 64-bit",
    url="https://github.com/snare/calculon",
    packages=['calculon'],
    install_requires=['Pyro4', 'blessed', 'scruffington'],
    package_data={'calculon': ['config/*']},
    entry_points={'console_scripts': ['calculon=calculon:main']},
    zip_safe=False
)
