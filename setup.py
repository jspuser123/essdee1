# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in essdee/__init__.py
from essdee import __version__ as version

setup(
	name='essdee',
	version=version,
	description='Customized Frappe app for Essdee Knitting Mills Pvt Ltd',
	author='Aerele Technologies Pvt Ltd',
	author_email='hello@aerele.in',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
