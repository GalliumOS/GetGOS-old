from setuptools import setup, find_packages

version = "2.4.9"

setup(
    name="GetGOS",
    version=version,
    packages=find_packages(),
    install_requires=['tornado==2.4', 'sqlalchemy', 'mako', 'python-android'],
    tests_require=['nose'],
    entry_points={
        'console_scripts': [
            'getgos.server=getgos.app:run_server',
            'getgos.addfile=getgos.utils.addfile:main',
            'getcm.fetchbuilds=getgos.utils.fetchbuilds:main',
        ],
    },
    include_package_data=True,
)
