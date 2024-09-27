from setuptools import setup, find_packages

setup(
    name='GetStam',  # Replace with your application name
    version='1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask==2.0.3',
        'requests==2.26.0',
        'pytz==2021.3',
        'python-dateutil==2.8.2',
    ],
    entry_points={
        'console_scripts': [
            'runapp = app:app',  # Change 'app' to your main file name if it's different
        ],
    },
)
