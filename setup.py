#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='target-hubspot',
    version='1.0.2',
    description='hotglue target for exporting data to Hubspot API',
    author='hotglue',
    url='https://hotglue.xyz',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    py_modules=['target_hubspot'],
    install_requires=[
        'requests==2.20.0',
        'pandas==1.3.4',
        'argparse==1.4.0',
        'singer-python==5.12.2',
        'xmltodict==0.12.0',
        'attrs==21.4.0'
    ],
    entry_points='''
        [console_scripts]
        target-hubspot=target_hubspot:main
    ''',
    packages=['target_hubspot'],
    package_data = {
        'target_hubspot/schemas': [
            "campaigns.json",
            "companies.json",
            "contact_lists.json",
            "contacts.json",
            "deals.json",
            "email_events.json",
            "forms.json",
            "keywords.json",
            "owners.json",
            "subscription_changes.json",
            "workflows.json",
        ],
    },
    include_package_data=True,
)
