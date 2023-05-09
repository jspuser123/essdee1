# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "essdee"
app_title = "Essdee"
app_publisher = "Aerele Technologies Pvt Ltd"
app_description = "Customized Frappe app for Essdee Knitting Mills Pvt Ltd"
app_icon = "octicon octicon-file-directory"
app_color = "blue"
app_email = "hello@aerele.in"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/essdee/css/essdee.css"
# app_include_js = "/assets/essdee/js/essdee.js"

# include js, css files in header of web template
# web_include_css = "/assets/essdee/css/essdee.css"
# web_include_js = "/assets/essdee/js/essdee.js"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Customer" : "public/js/customer.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "essdee.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "essdee.install.before_install"
after_install = "essdee.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "essdee.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.validate_zero_rate",
		"before_insert": "essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.set_field_values",
		"validate": ["essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.set_tcs", "essdee.essdee.utils.sales_invoice.insert_essdee_discount_template", "essdee.essdee.utils.sales_invoice.calculate_essdee_discount"]
	},
	"Purchase Invoice": {
		"validate": "essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.set_tds"
	},
	"Prepared Report":{
		"on_change": "essdee.essdee.report.agent_late_payment.agent_late_payment.create_send_document"
	}
}
#TODO: Alter these functions when base functions changed.
override_whitelisted_methods = {
	"erpnext.regional.india.e_invoice.utils.get_einvoice": "essdee.essdee.utils.sales_invoice.get_einvoice",
	"erpnext.regional.india.e_invoice.utils.generate_irn": "essdee.essdee.utils.sales_invoice.generate_irn",
	"erpnext.regional.india.e_invoice.utils.cancel_eway_bill": "essdee.essdee.utils.sales_invoice.cancel_eway_bill",
	"erpnext.regional.india.e_invoice.utils.generate_eway_bill": "essdee.essdee.utils.sales_invoice.generate_eway_bill"
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
	# "all": [
	# 	"essdee.tasks.all"
	# ],
	# "daily": [
	# 	"essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.sync_data"
	# ],
	# "hourly": [
	# 	"essdee.tasks.hourly"
	# ],
	# "weekly": [
	# 	"essdee.tasks.weekly"
	# ]
	# "monthly": [
	# 	"essdee.tasks.monthly"
	# ]
# }

# Testing
# -------

# before_tests = "essdee.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "essdee.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "essdee.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# doc_events = {
# 	"Sales Invoice": {
# 		"validate": "essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.add_special_discount"
# 	}
# }

jenv = {
    "methods": [
        "sd_get_qty_in_boxes:essdee.essdee.utils.sales_invoice.sd_get_qty_in_boxes",
		"sd_get_total_qty:essdee.essdee.utils.sales_invoice.sd_get_total_qty"
		
    ]
}
