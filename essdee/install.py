from __future__ import unicode_literals
from essdee.essdee.doctype.essdee_application_settings.essdee_application_settings import create_custom_field

def after_install():
	create_custom_field()