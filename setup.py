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
    install_requires = [],
    package_data = {'calculon': ['config/*']},
    install_package_data = True,
    entry_points = {'console_scripts': ['calculon = calculon:main']},
    zip_safe=False
)
