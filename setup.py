from setuptools import setup, find_packages

setup(
    name='zkit',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'flask_sqlalchemy',
        'flask_restful',
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'zkit = zkit.run:main',
        ],
    },
)
