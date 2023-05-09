import frappe
import erpnext
from erpnext.regional.india.e_invoice.utils import *
from erpnext.regional.india.utils import get_gst_accounts
from essdee.essdee.doctype.essdee_application_settings.essdee_application_settings import validate_zero_rate
from frappe import _
from six import string_types
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from frappe.utils.data import cint, flt
from erpnext.regional.india.utils import update_taxable_values
from erpnext.stock.get_item_details import get_conversion_factor

@frappe.whitelist()
def get_einvoice(doctype, docname):
	invoice = frappe.get_doc(doctype, docname)
	validate_zero_rate(invoice, 'on_submit')
	settings = frappe.get_single('Essdee Application Settings')
	einvoice = make_einvoice(invoice)

	if settings.is_stock_item or settings.enable_unit_mapping:
		einvoice['ItemList'] = get_item_list_custom(einvoice['ItemList'], settings)
	
	if settings.enable_custom_e_invoice:
		einvoice = update_calculated_values(invoice, einvoice)

	if settings.based_on_transporter_id and 'EwbDtls' in einvoice:
		einvoice['EwbDtls'] = update_ewb_json(einvoice['EwbDtls'])

	validate_totals(einvoice)
	return einvoice

def update_ewb_json(ewb_details):
	if isinstance(ewb_details, string_types):
		ewb_details = json.loads(ewb_details)

	if "TransId" in ewb_details and ewb_details["TransId"]:
		if "TransDocNo" in ewb_details:
			del ewb_details["TransDocNo"]
		if "TransMode" in ewb_details:
			del ewb_details["TransMode"]
		if "VehNo" in ewb_details:
			del ewb_details["VehNo"]
		if "VehType" in ewb_details:
			del ewb_details["VehType"]

	return ewb_details

def update_calculated_values(invoice, einvoice):
	current_taxable_amount = 0
	for item in invoice.items:
		current_taxable_amount += abs(item.base_amount)
	cal_values = calculate_amounts(invoice)
	invoice_value_details = einvoice['ValDtls']
	invoice_value_details["AssVal"] = cal_values['totalValue']
	invoice_value_details["CgstVal"]= cal_values['cgstValue']
	invoice_value_details["SgstVal"] = cal_values['sgstValue']
	invoice_value_details["IgstVal"] = cal_values['igstValue']
	invoice_value_details["OthChrg"] = cal_values['OthValue']
	# invoice_value_details["Discount"] = round(current_taxable_amount - cal_values['totalValue'], 2)

	for item in einvoice['ItemList']:
		item = update_item_values(item, cal_values['totalValue'], current_taxable_amount)

	return einvoice

def get_item_list_custom(items, settings):
	unit_mapping = {'Kg': 'Kgs', 'Pieces': 'Pcs', 'Unit': 'Unt'}
	for item in items:
		if settings.is_stock_item:
			item["IsServc"] = 'N'
		if settings.enable_unit_mapping and item["Unit"] in unit_mapping:
			item["Unit"] = unit_mapping[item["Unit"]]
	return items

def update_item_values(item, actual_taxable_amount, current_taxable_amount):
	# item["AssAmt"] = abs(round(item["TotAmt"] - ((item["TotAmt"]/current_taxable_amount) * (current_taxable_amount - actual_taxable_amount)), 2))
	item["TotAmt"] = abs(round(item["AssAmt"] + ((item["AssAmt"]/actual_taxable_amount) * (current_taxable_amount - actual_taxable_amount)), 2))
	item["UnitPrice"] = round(item["TotAmt"]/item["Qty"], 2)
	item["Discount"] = round(item["TotAmt"] - item["AssAmt"], 2)
	if not item["IgstAmt"] == 0:
		item["IgstAmt"] = abs(round(item["AssAmt"] * (item["GstRt"]/100), 2))
	if not item["CgstAmt"] == 0:
		item["CgstAmt"] = abs(round(item["AssAmt"] * (item["GstRt"]/200), 2))
	if not item["SgstAmt"] == 0:
		item["SgstAmt"] = abs(round(item["AssAmt"] * (item["GstRt"]/200), 2))
	item["TotItemVal"] = abs(round(item["AssAmt"] + item["IgstAmt"] + item["SgstAmt"] + item["CgstAmt"], 2))
	return item

def calculate_amounts(sinv_doc):
	total_taxable_amount_set = {'bool':0}
	total_taxable_amount = {'amount':0.0}
	cgst_amount = []
	sgst_amount = []
	igst_amount = []
	gst_account_heads = get_gst_accounts(sinv_doc.company, True)
	for row in sinv_doc.taxes:
		if row.account_head in gst_account_heads:
			if total_taxable_amount_set['bool'] == 0:
				total_taxable_amount_set.update({'bool': 1})
				total_taxable_amount.update({'amount': row.total - row.tax_amount})
			if gst_account_heads[row.account_head] == 'cgst_account':
				cgst_amount.append(row.tax_amount*1.0)
			elif gst_account_heads[row.account_head] == 'sgst_account':
				sgst_amount.append(row.tax_amount*1.0)
			elif gst_account_heads[row.account_head] == 'igst_account':
				igst_amount.append(row.tax_amount*1.0)
	return {
		'totalValue': abs(round(total_taxable_amount['amount'],2)),
		'cgstValue': abs(sum(cgst_amount)),
		'sgstValue': abs(sum(sgst_amount)),
		'igstValue': abs(sum(igst_amount)),
		'OthValue': abs(round(sinv_doc.grand_total - (total_taxable_amount['amount'] + sum(cgst_amount) + sum(sgst_amount) + sum(igst_amount)),2))
	}

@frappe.whitelist()
def generate_irn(doctype, docname):
	GSPConnector.set_einvoice_data = set_einvoice_data_custom
	gsp_connector = GSPConnector(doctype, docname)
	headers = gsp_connector.get_headers()
	settings = frappe.get_single('Essdee Application Settings')
	einvoice = get_einvoice(doctype, docname)
	data = json.dumps(einvoice, indent=4)

	try:
		res = gsp_connector.make_request('post', gsp_connector.generate_irn_url, headers, data)
		if res.get('success'):
			gsp_connector.set_einvoice_data(res.get('result'))

		elif '2150' in res.get('message'):
			# IRN already generated but not updated in invoice
			# Extract the IRN from the response description and fetch irn details
			irn = res.get('result')[0].get('Desc').get('Irn')
			irn_details = gsp_connector.get_irn_details(irn)
			if irn_details:
				gsp_connector.set_einvoice_data(irn_details)
			else:
				raise RequestFailed('IRN has already been generated for the invoice but cannot fetch details for the it. \
					Contact ERPNext support to resolve the issue.')

		else:
			raise RequestFailed
	
	except RequestFailed:
		errors = gsp_connector.sanitize_error_message(res.get('message'))
		gsp_connector.raise_error(errors=errors)

	except Exception:
		log_error(data)
		gsp_connector.raise_error(True)

def set_einvoice_data_custom(self, res):
	enc_signed_invoice = res.get('SignedInvoice')
	dec_signed_invoice = jwt.decode(enc_signed_invoice, verify=False)['data']

	self.invoice.irn = res.get('Irn')
	ewaybill = res.get('EwbNo')
	if ewaybill:
		self.invoice.ewaybill = ewaybill
		from datetime import datetime
		self.invoice.ewaybill_date = datetime.strptime(res.get('EwbDt'), '%Y-%m-%d %H:%M:%S')
		validity = res.get('EwbValidTill')
		if validity:
			self.invoice.ewaybill_validity = datetime.strptime(validity, '%Y-%m-%d %H:%M:%S')
	self.invoice.ack_no = res.get('AckNo')
	self.invoice.ack_date = res.get('AckDt')
	self.invoice.signed_einvoice = dec_signed_invoice
	self.invoice.signed_qr_code = res.get('SignedQRCode')

	self.attach_qrcode_image()

	self.invoice.flags.updater_reference = {
		'doctype': self.invoice.doctype,
		'docname': self.invoice.name,
		'label': _('IRN Generated')
	}
	self.update_invoice()

def generate_eway_bill_custom(self, **kwargs):
	args = frappe._dict(kwargs)

	headers = self.get_headers()
	eway_bill_details = get_eway_bill_details(args)
	data = json.dumps({
		'Irn': args.irn,
		'Distance': cint(eway_bill_details.distance),
		'TransMode': eway_bill_details.mode_of_transport,
		'TransId': eway_bill_details.gstin,
		'TransName': eway_bill_details.transporter,
		'TrnDocDt': eway_bill_details.document_date,
		'TrnDocNo': eway_bill_details.document_name,
		'VehNo': eway_bill_details.vehicle_no,
		'VehType': eway_bill_details.vehicle_type
	}, indent=4)
	enabled = frappe.db.get_single_value('Essdee Application Settings', 'based_on_transporter_id')
	if enabled:
		data = update_ewb_json(data)
	try:
		res = self.make_request('post', self.generate_ewaybill_url, headers, json.dumps(data))
		if res.get('success'):
			self.invoice.ewaybill = res.get('result').get('EwbNo')
			self.invoice.eway_bill_cancelled = 0
			self.invoice.update(args)
			self.invoice.flags.updater_reference = {
				'doctype': self.invoice.doctype,
				'docname': self.invoice.name,
				'label': _('E-Way Bill Generated')
			}
			self.update_invoice()

		else:
			raise RequestFailed

	except RequestFailed:
		errors = self.sanitize_error_message(res.get('message'))
		self.raise_error(errors=errors)

	except Exception:
		log_error(data)
		self.raise_error(True)

@frappe.whitelist()
def cancel_eway_bill(doctype, docname, eway_bill, reason, remark):
	GSPConnector.set_einvoice_data = set_einvoice_data_custom
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.cancel_eway_bill(eway_bill, reason, remark)

@frappe.whitelist()
def generate_eway_bill(doctype, docname, **kwargs):
	gsp_connector = GSPConnector(doctype, docname)
	GSPConnector.generate_eway_bill = generate_eway_bill_custom
	gsp_connector.generate_eway_bill(**kwargs)


# Essdee Discount 
def insert_essdee_discount_template(doc, action):
	settings = frappe.get_single('Essdee Application Settings')
	default_sales_invoice_discounts = settings.default_sales_invoice_discounts
	enable_default_discounts_insertion = cint(settings.enable_default_discounts_insertion)
	if action == "validate" and enable_default_discounts_insertion and len(doc.sd_discounts) < 1 and doc.docstatus == 0:
		if default_sales_invoice_discounts:
			discount_table_fields = frappe.get_meta("SD Sales Invoice Discount").fields
			for discount in default_sales_invoice_discounts:
				sd_discount = {}
				if cint(doc.is_return) and flt(discount.sd_discount_amount):
					discount.sd_discount_amount *= -1
				for field in discount_table_fields:
					sd_discount[field.fieldname] = discount.get(field.fieldname)
				doc.append("sd_discounts", sd_discount)

def calculate_essdee_discount(doc, action):
	if action == "validate" and len(doc.sd_discounts) > 0 and doc.docstatus == 0:
		net_total = doc.total
		total_discount = 0
		for discount in doc.sd_discounts:
			if not flt(discount.sd_discount_percentage) and not flt(discount.sd_discount_amount) and not discount.sd_discount_total:
				continue
			if flt(discount.sd_discount_percentage) < 0:
				frappe.throw(_(f'Essdee Discount Percentage at Row {discount.idx} must be Positive'))
			if not cint(doc.is_return) and flt(discount.sd_discount_amount) < 0:
				frappe.throw(_(f'Essdee Discount Amount at Row {discount.idx} must be Positive'))
			if cint(doc.is_return) and  flt(discount.sd_discount_amount) > 0:
				frappe.throw(_(f'Essdee Discount Amount at Row {discount.idx} must be Negative'))
			if discount.sd_discount_type == "Actual":
				if flt(discount.sd_discount_percentage):
					frappe.throw(_(f'Invalid Discount at Essdee Discount Row {discount.idx}'))
				net_total -= flt(discount.sd_discount_amount)
				total_discount += flt(discount.sd_discount_amount)
				discount.sd_discount_total = flt(discount.sd_discount_amount)
			if discount.sd_discount_type == "Based on Percentage":
				if flt(discount.sd_discount_amount):
					frappe.throw(_(f'Invalid Discount at Essdee Discount Row {discount.idx}'))
				discount_amt = net_total * (flt(discount.sd_discount_percentage)/100)
				net_total -= discount_amt
				total_discount += discount_amt
				discount.sd_discount_total = discount_amt
		if abs(total_discount) > 0:
			doc.apply_discount_on = "Net Total"
			doc.discount_amount = total_discount
			calculate_taxes_and_totals(doc)
			update_taxable_values(doc, action)


@frappe.whitelist()
def sd_get_qty_in_boxes(item_code, uom, qty, append_uom=True):
	box_qty = None
	if uom == "Box":
		box_qty = flt(qty)
	if uom == "Pieces":
		conversion_factor = get_conversion_factor(item_code, "Box").get('conversion_factor')
		if conversion_factor:
			box_qty = flt(qty)/flt(conversion_factor)
	if box_qty is None:
		return "-"
	if box_qty - cint(box_qty) != 0:
		frappe.throw("Box Qty needs to be Whole Number. Error in sd_get_qty_in_boxes function.")
	if append_uom:
		box_qty = f'{cint(box_qty)} Box'
	return box_qty

@frappe.whitelist()
def sd_get_total_qty(items):
	total_boxes = 0
	total_qty = 0
	uom = items[0].uom
	for item in items:
		total_qty += flt(item.qty)
		total_boxes += cint(sd_get_qty_in_boxes(item.item_code, item.stock_uom, item.stock_qty, False))
	return {
		"total_boxes": f'{cint(total_boxes)} Box' if total_boxes != 0 else '-',
		"total_qty": f'{total_qty} {uom}' if total_qty != 0 else '-'
	}
