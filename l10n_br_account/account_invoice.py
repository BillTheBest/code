# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
# Copyright (C) 2009  Renato Lima - Akretion                                    #
#                                                                               #
#This program is free software: you can redistribute it and/or modify           #
#it under the terms of the GNU Affero General Public License as published by    #
#the Free Software Foundation, either version 3 of the License, or              #
#(at your option) any later version.                                            #
#                                                                               #
#This program is distributed in the hope that it will be useful,                #
#but WITHOUT ANY WARRANTY; without even the implied warranty of                 #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                  #
#GNU Affero General Public License for more details.                            #
#                                                                               #
#You should have received a copy of the GNU Affero General Public License       #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.          #
#################################################################################

from lxml import etree
from lxml.etree import ElementTree
from lxml.etree import Element, SubElement
import time
from datetime import datetime
import netsvc
import re
import string
from unicodedata import normalize

from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_tax_discount': 0.0,
                'amount_total': 0.0,
                'icms_base': 0.0,
                'icms_value': 0.0,
                'icms_st_base': 0.0,
                'icms_st_value': 0.0,
                'ipi_base': 0.0,
                'ipi_value': 0.0,
                'pis_base': 0.0,
                'pis_value': 0.0,
                'cofins_base': 0.0,
                'cofins_value': 0.0,
                'ii_value': 0.0,
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_total
                res[invoice.id]['icms_base'] += line.icms_base
                res[invoice.id]['icms_value'] += line.icms_value
                res[invoice.id]['icms_st_base'] += line.icms_st_base
                res[invoice.id]['icms_st_value'] += line.icms_st_value
                res[invoice.id]['ipi_base'] += line.ipi_base
                res[invoice.id]['ipi_value'] += line.ipi_value
                res[invoice.id]['pis_base'] += line.pis_base
                res[invoice.id]['pis_value'] += line.pis_value
                res[invoice.id]['cofins_base'] += line.cofins_base
                res[invoice.id]['cofins_value'] += line.cofins_value
                res[invoice.id]['ii_value'] += line.ii_value
           
            for invoice_tax in invoice.tax_line:
                if not invoice_tax.tax_code_id.tax_discount:
                    res[invoice.id]['amount_tax'] += invoice_tax.amount

            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']
        return res
    
    def _get_fiscal_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('fiscal_type', 'product')
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        result = super(account_invoice,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

        if context is None:
            context = {}

        field_names = ['service_type_id']
        result['fields'].update(self.fields_get(cr, uid, field_names, context))

        if not view_type:
            view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'account.invoice.tree')])
            view_type = 'tree'

        if view_type == 'form':
            
            eview = etree.fromstring(result['arch'])
            
            if 'type' in context.keys():

                operation_type = {'out_invoice': 'output', 'in_invoice': 'input', 'out_refund': 'input', 'in_refund': 'output'}
                    
                fiscal_types = eview.xpath("//field[@name='invoice_line']")
                for fiscal_type in fiscal_types:
                    fiscal_type.set('context', "{'type': '%s', 'fiscal_type': '%s'}" % (context['type'], context.get('fiscal_type', 'product'),))

                fiscal_operation_categories = eview.xpath("//field[@name='fiscal_operation_category_id']")
                for fiscal_operation_category_id in fiscal_operation_categories:
                    fiscal_operation_category_id.set('domain', "[('fiscal_type','=','product'),('type','=','%s'),('use_invoice','=',True)]" % (operation_type[context['type']],))
                    fiscal_operation_category_id.set('required', '1')
                    
                fiscal_operations = eview.xpath("//field[@name='fiscal_operation_id']")
                for fiscal_operation_id in fiscal_operations:
                    fiscal_operation_id.set('domain', "[('fiscal_type','=','product'),('type','=','%s'),('fiscal_operation_category_id','=',fiscal_operation_category_id),('use_invoice','=',True)]" % (operation_type[context['type']],))
                    fiscal_operation_id.set('required', '1')
    
            if context.get('fiscal_type', False) == 'service':
                
                delivery_infos = eview.xpath("//group[@name='delivery_info']")
                for delivery_info in delivery_infos:
                    delivery_info.set('invisible', '1')
                
                cfops = eview.xpath("//field[@name='cfop_ids']")
                for cfop_ids in cfops:
                    cfop_ids.set('name', 'service_type_id')
                    cfop_ids.set('domain', '[]')
                
                document_series = eview.xpath("//field[@name='document_serie_id']")
                for document_serie_id in document_series:
                    document_serie_id.set('domain', "[('fiscal_type','=','service')]")
        
                if context['type'] in ('in_invoice', 'out_refund'):    
                    fiscal_operation_categories = eview.xpath("//field[@name='fiscal_operation_category_id']")
                    for fiscal_operation_category_id in fiscal_operation_categories:
                        fiscal_operation_category_id.set('domain', "[('fiscal_type','=','service'),('type','=','input'),('use_invoice','=',True)]")
                        fiscal_operation_category_id.set('required', '1')
                        
                    fiscal_operations = eview.xpath("//field[@name='fiscal_operation_id']")
                    for fiscal_operation_id in fiscal_operations:
                        fiscal_operation_id.set('domain', "[('fiscal_type','=','service'),('type','=','input'),('fiscal_operation_category_id','=',fiscal_operation_category_id),('use_invoice','=',True)]")
                        fiscal_operation_id.set('required', '1')
                
                if context['type'] in ('out_invoice', 'in_refund'):  
                    fiscal_operation_categories = eview.xpath("//field[@name='fiscal_operation_category_id']")
                    for fiscal_operation_category_id in fiscal_operation_categories:
                        fiscal_operation_category_id.set('domain', "[('fiscal_type','=','service'),('type','=','output'),('use_invoice','=',True)]")
                        fiscal_operation_category_id.set('required', '1')
                    
                    fiscal_operations = eview.xpath("//field[@name='fiscal_operation_id']")
                    for fiscal_operation_id in fiscal_operations:
                        fiscal_operation_id.set('domain', "[('fiscal_type','=','service'),('type','=','output'),('fiscal_operation_category_id','=',fiscal_operation_category_id),('use_invoice','=',True)]")
                        fiscal_operation_id.set('required', '1')
            
            result['arch'] = etree.tostring(eview)
        
        if view_type == 'tree':
            doc = etree.XML(result['arch'])
            nodes = doc.xpath("//field[@name='partner_id']")
            partner_string = _('Customer')
            if context.get('type', 'out_invoice') in ('in_invoice', 'in_refund'):
                partner_string = _('Supplier')
            for node in nodes:
                node.set('string', partner_string)
            result['arch'] = etree.tostring(doc)
        return result

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    def _get_cfops(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            id = invoice.id
            result[id] = []
            new_ids = []
            for line in invoice.invoice_line:
                if line.cfop_id and not line.cfop_id.id in new_ids:
                    new_ids.append(line.cfop_id.id)
            new_ids.sort()
            result[id] = new_ids
        return result

    def _get_receivable_lines(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            id = invoice.id
            res[id] = []
            if not invoice.move_id:
                continue
            data_lines = [x for x in invoice.move_id.line_id if x.account_id.id == invoice.account_id.id and x.account_id.type in ('receivable', 'payable') and invoice.journal_id.revenue_expense]
            New_ids = []
            for line in data_lines:
                New_ids.append(line.id)
                New_ids.sort()
            res[id] = New_ids
        return res
    
    _columns = {
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('sefaz_export','Enviar para Receita'),
            ('sefaz_exception','Erro de autorização da Receita'),
            ('paid','Paid'),
            ('cancel','Cancelled')
            ],'State', select=True, readonly=True,
            help=' * The \'Draft\' state is used when a user is encoding a new and unconfirmed Invoice. \
            \n* The \'Pro-forma\' when invoice is in Pro-forma state,invoice does not have an invoice number. \
            \n* The \'Open\' state is used when user create invoice,a invoice number is generated.Its in open state till user does not pay invoice. \
            \n* The \'Paid\' state is set automatically when invoice is paid.\
            \n* The \'sefaz_out\' Gerado aquivo de exportação para sistema daReceita.\
            \n* The \'sefaz_aut\' Recebido arquivo de autolização da Receita.\
            \n* The \'Cancelled\' state is used when user cancel invoice.'),
        'partner_shipping_id': fields.many2one('res.partner.address', 'Endereço de Entrega', readonly=True, states={'draft': [('readonly', False)]}, help="Shipping address for current sales order."),
        'own_invoice': fields.boolean('Nota Fiscal Própria',readonly=True, states={'draft':[('readonly',False)]}),
        'internal_number': fields.char('Invoice Number', size=32, readonly=True , states={'draft':[('readonly',False)]}, help="Unique number of the invoice, computed automatically when the invoice is created."),
        'vendor_serie': fields.char('Série NF Entrada', size=12, readonly=True, states={'draft':[('readonly',False)]}, help="Série do número da Nota Fiscal do Fornecedor"),
        'nfe_access_key': fields.char('Chave de Acesso NFE', size=44, readonly=True, states={'draft':[('readonly',False)]}),
        'nfe_status': fields.char('Status na Sefaz', size=44, readonly=True),
        'nfe_date': fields.datetime('Data do Status NFE', readonly=True),
        'nfe_export_date': fields.datetime('Exportação NFE', readonly=True),
        'fiscal_document_id': fields.many2one('l10n_br_account.fiscal.document', 'Documento',  readonly=True, states={'draft':[('readonly',False)]}),
        'fiscal_document_nfe': fields.related('fiscal_document_id', 'nfe', type='boolean', readonly=True, relation='l10n_br_account.fiscal.document', store=True, string='NFE'),
        'fiscal_type': fields.selection([('product', 'Produto'), ('service', 'Serviço')], 'Tipo Fiscal', requeried=True),
        'move_line_receivable_id': fields.function(_get_receivable_lines, method=True, type='many2many', relation='account.move.line', string='Entry Lines'),
        'document_serie_id': fields.many2one('l10n_br_account.document.serie', 'Série', domain="[('fiscal_document_id','=',fiscal_document_id),('company_id','=',company_id)]", readonly=True, states={'draft':[('readonly',False)]}),
        'fiscal_operation_category_id': fields.many2one('l10n_br_account.fiscal.operation.category', 'Categoria', readonly=True, states={'draft':[('readonly',False)]}),
        'fiscal_operation_id': fields.many2one('l10n_br_account.fiscal.operation', 'Operação Fiscal', domain="[('fiscal_operation_category_id','=',fiscal_operation_category_id)]", readonly=True, states={'draft':[('readonly',False)]}),
        'cfop_ids': fields.function(_get_cfops, method=True, type='many2many', relation='l10n_br_account.cfop', string='CFOP'),
        'service_type_id': fields.many2one('l10n_br_account.service.type', 'Tipo de Serviço', readonly=True, states={'draft':[('readonly',False)]}),
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Untaxed',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Tax',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'amount_total': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'icms_base': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Base ICMS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'icms_value': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Valor ICMS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'icms_st_base': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Base ICMS ST',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'icms_st_value': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Valor ICMS ST',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
            
        'ipi_base': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Base IPI',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'ipi_value': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Valor IPI',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
         'pis_base': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Base PIS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'pis_value': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Valor PIS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'cofins_base': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Base COFINS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'cofins_value': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Valor COFINS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
        'ii_value': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Valor II',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount'], 20),
            },
            multi='all'),
    }
    
    def _default_fiscal_operation_category(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        default_fo_category_product = {'in_invoice': 'in_invoice_fiscal_category_operation_id', 
                                       'out_invoice': 'out_invoice_fiscal_category_operation_id',
                                       'in_refund': 'in_refund_fiscal_category_operation_id', 
                                       'out_refund': 'out_refund_fiscal_category_operation_id'}
        default_fo_category_service = {'in_invoice': 'in_invoice_service_fiscal_category_operation_id', 
                                       'out_invoice': 'out_invoice_service_fiscal_category_operation_id'}
        default_fo_category = {
                               'product': default_fo_category_product, 
                               'service': default_fo_category_service,
                               }
        invoice_type = context.get('type', 'out_invoice')
        invoice_fiscal_type = context.get('fiscal_type', 'product')
        fo_category = self.pool.get('res.company').read(cr, uid, user.company_id.id, [default_fo_category[invoice_fiscal_type][invoice_type]], context=context)[default_fo_category[invoice_fiscal_type][invoice_type]]
        return fo_category and fo_category[0] or False
    
    _defaults = {
                 'own_invoice': True,
                 'fiscal_type': _get_fiscal_type,
                 'fiscal_operation_category_id': _default_fiscal_operation_category,
                 }

    def _check_invoice_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoices = self.browse(cr, uid, ids, context=context)
        domain = []
        for invoice in invoices:
            if not invoice.number:
                continue
            fiscal_document = invoice.fiscal_document_id and invoice.fiscal_document_id.id or False
            domain.extend([('internal_number','=',invoice.number),
                           ('fiscal_type','=',invoice.fiscal_type),
                           ('fiscal_document_id','=',fiscal_document)
                           ])                
            if invoice.own_invoice:
                domain.extend([('company_id','=',invoice.company_id.id),
                              ('internal_number','=',invoice.number),
                              ('fiscal_document_id','=',invoice.fiscal_document_id.id),
                              ('own_invoice','=',True)])
            else:
                domain.extend([('partner_id','=',invoice.partner_id.id),
                              ('vendor_serie','=',invoice.vendor_serie),
                              ('own_invoice','=',False)])
                
            invoice_id = self.pool.get('account.invoice').search(cr, uid, domain)
            if len(invoice_id) > 1:
                    return False
        return True

    _constraints = [
                    (_check_invoice_number,
                     u"Error!\nNão é possível registrar \
                     documentos fiscais com números repetidos.",
                     ['number']),
    ]

    def init(self, cr):
        # Remove a constraint na coluna número do documento fiscal,
        # no caso dos documentos de entradas dos fornecedores pode existir
        # documentos fiscais de fornecedores diferentes com a mesma numeração
        cr.execute("ALTER TABLE %s DROP CONSTRAINT IF EXISTS %s" % ('account_invoice', 'account_invoice_number_uniq'))

    # go from canceled state to draft state
    def action_cancel_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'draft', 'internal_number':False, 'nfe_access_key':False, 
                                  'nfe_status':False, 'nfe_date':False, 'nfe_export_date':False})
        wf_service = netsvc.LocalService("workflow")
        for inv_id in ids:
            wf_service.trg_delete(uid, 'account.invoice', inv_id, cr)
            wf_service.trg_create(uid, 'account.invoice', inv_id, cr)
        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'internal_number': False,
            'nfe_access_key': False,
            'nfe_status': False,
            'nfe_date': False,
            'nfe_export_date': False,
        })
        return super(account_invoice, self).copy(cr, uid, id, default, context)

    def action_internal_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        for obj_inv in self.browse(cr, uid, ids):
            if obj_inv.own_invoice:
                obj_sequence = self.pool.get('ir.sequence')
                seq_no = obj_sequence.get_id(cr, uid, obj_inv.document_serie_id.internal_sequence_id.id, context=context)
                self.write(cr, uid, obj_inv.id, {'internal_number': seq_no})
        
        return True

    def action_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #TODO: not correct fix but required a frech values before reading it.
        self.write(cr, uid, ids, {})

        for obj_inv in self.browse(cr, uid, ids, context=context):
            inv_id = obj_inv.id
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            ref = obj_inv.internal_number or obj_inv.reference or ''

            cr.execute('UPDATE account_move SET ref=%s ' \
                    'WHERE id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_move_line SET ref=%s ' \
                    'WHERE move_id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                    'FROM account_move_line ' \
                    'WHERE account_move_line.move_id = %s ' \
                        'AND account_analytic_line.move_id = account_move_line.id',
                        (ref, move_id))

            for inv_id, name in self.name_get(cr, uid, [inv_id]):
                ctx = context.copy()
                if obj_inv.type in ('out_invoice', 'out_refund'):
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _('Invoice ') + " '" + name + "' " + _("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)
        return True

    def action_move_create(self, cr, uid, ids, *args):
        result = super(account_invoice, self).action_move_create(cr, uid, ids, *args)
        for inv in self.browse(cr, uid, ids):
            if inv.move_id:
                self.pool.get('account.move').write(cr, uid, [inv.move_id.id], {'ref': inv.internal_number})
                for move_line in inv.move_id.line_id:    
                    self.pool.get('account.move.line').write(cr, uid, [move_line.id], {'ref': inv.internal_number})   
                move_lines = [x for x in inv.move_id.line_id if x.account_id.id == inv.account_id.id and x.account_id.type in ('receivable', 'payable')]
                i = len(move_lines)
                for move_line in move_lines:
                    move_line_name = '%s/%s' % (inv.internal_number, i)
                    self.pool.get('account.move.line').write(cr, uid, [move_line.id], {'name': move_line_name})   
                    i -= 1
        return result

    def nfe_dv(self, key):
        #Testing
        return '2'

    def nfe_check(self, cr, uid, ids, context=None):
        strErro = u''
        
        if context is None:
            context = {}
        
        for inv in self.browse(cr, uid, ids):
            
            #Nota fiscal
            if not inv.own_invoice or inv.fiscal_type == 'service' or not inv.fiscal_document_nfe:
                continue
            
            company_addr = self.pool.get('res.partner').address_get(cr, uid, [inv.company_id.partner_id.id], ['default'])
            company_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [company_addr['default']], context={'lang': 'pt_BR'})[0]
            
            if not inv.document_serie_id:
                strErro = u'Nota Fiscal - Série da nota fiscal\n'
            
            if not inv.fiscal_document_id:
                strErro += u'Nota Fiscal - Tipo de documento fiscal\n'
            
            #if not inv.date_invoice:
            #    strErro = 'Nota Fiscal - Data da nota fiscal\n'
            
            if not inv.document_serie_id.internal_sequence_id:
                strErro += u'Nota Fiscal - Número da nota fiscal, a série deve ter uma sequencia interna\n'

            #Emitente
            if not inv.company_id.partner_id.legal_name:
                strErro += u'Emitente - Razão Social\n'

            if not inv.company_id.partner_id.name:
                strErro += u'Emitente - Fantasia\n'

            if not inv.company_id.partner_id.cnpj_cpf:
                strErro += u'Emitente - CNPJ/CPF\n'

            if not company_addr_default.street:
                strErro += u'Emitente / Endereço - Logradouro\n'
            
            if not company_addr_default.number:
                strErro += u'Emitente / Endereço - Número\n'
                
            if not company_addr_default.zip:
                strErro += u'Emitente / Endereço - CEP\n'

            if not inv.company_id.cnae_main_id:
                strErro += u'Emitente / CNAE Principal\n'
                
            if not inv.company_id.partner_id.inscr_est:
                strErro += u'Emitente / Inscrição Estadual\n'

            if not company_addr_default.state_id:
                strErro += u'Emitente / Endereço - Estado\n'
            else:
                if not company_addr_default.state_id.ibge_code:
                    strErro += u'Emitente / Endereço - Código do IBGE do estado\n'
                if not company_addr_default.state_id.name:
                    strErro += u'Emitente / Endereço - Nome do estado\n'
                      
            if not company_addr_default.l10n_br_city_id:
                strErro += u'Emitente / Endereço - município\n'
            else:
                if not company_addr_default.l10n_br_city_id.name:
                    strErro += u'Emitente / Endereço - Nome do município\n'
                if not company_addr_default.l10n_br_city_id.ibge_code:
                    strErro += u'Emitente / Endereço - Código do IBGE do município\n'
                    
            if not company_addr_default.country_id:
                strErro += u'Emitente / Endereço - país\n'
            else:
                if not company_addr_default.country_id.name:
                    strErro += u'Emitente / Endereço - Nome do país\n'
                if not company_addr_default.country_id.bc_code:
                    strErro += u'Emitente / Endereço - Código do BC do país\n'
        
            #Destinatário
            if inv.partner_id.tipo_pessoa == 'J' and not inv.partner_id.legal_name:
                strErro += u'Destinatário - Razão Social\n'
            
            if not inv.partner_id.cnpj_cpf:
                strErro += u'Destinatário - CNPJ/CPF\n'
            
            if not inv.address_invoice_id.street:
                strErro += u'Destinatário / Endereço - Logradouro\n'
            
            if not inv.address_invoice_id.number:
                strErro += u'Destinatário / Endereço - Número\n'
            
            if inv.address_invoice_id.country_id.id == company_addr_default.country_id.id:
                if not inv.address_invoice_id.zip:
                    strErro += u'Destinatário / Endereço - CEP\n'

            if inv.address_invoice_id.country_id.id == company_addr_default.country_id.id:
                if not inv.address_invoice_id.state_id:
                    strErro += u'Destinatário / Endereço - Estado\n'
                else:
                    if not inv.address_invoice_id.state_id.ibge_code:
                        strErro += u'Destinatário / Endereço - Código do IBGE do estado\n'
                    if not inv.address_invoice_id.state_id.name:
                        strErro += u'Destinatário / Endereço - Nome do estado\n'
            
            if inv.address_invoice_id.country_id.id == company_addr_default.country_id.id:
                if not inv.address_invoice_id.l10n_br_city_id:
                    strErro += u'Destinatário / Endereço - Município\n'
                else:
                    if not inv.address_invoice_id.l10n_br_city_id.name:
                        strErro += u'Destinatário / Endereço - Nome do município\n'
                    if not inv.address_invoice_id.l10n_br_city_id.ibge_code:
                        strErro += u'Destinatário / Endereço - Código do IBGE do município\n'

            if not inv.address_invoice_id.country_id:
                strErro += u'Destinatário / Endereço - País\n'
            else:
                if not inv.address_invoice_id.country_id.name:
                    strErro += u'Destinatário / Endereço - Nome do país\n'
                if not inv.address_invoice_id.country_id.bc_code:
                    strErro += u'Destinatário / Endereço - Código do BC do país\n'

            #endereco de entrega
            if inv.partner_shipping_id:
                
                if inv.address_invoice_id != inv.partner_shipping_id: 
                    
                    if not inv.partner_shipping_id.street:
                        strErro += u'Destinatário / Endereço de Entrega - Logradouro\n'
                    
                    if not inv.partner_shipping_id.number:
                        strErro += u'Destinatário / Endereço de Entrega - Número\n'
                        
                    if not inv.address_invoice_id.zip:
                        strErro += u'Destinatário / Endereço de Entrega - CEP\n'
        
                    if not inv.partner_shipping_id.state_id:
                        strErro += u'Destinatário / Endereço de Entrega - Estado\n'
                    else:
                        if not inv.partner_shipping_id.state_id.ibge_code:
                            strErro += u'Destinatário / Endereço de Entrega - Código do IBGE do estado\n'
                        if not inv.partner_shipping_id.state_id.name:
                            strErro += u'Destinatário / Endereço de Entrega - Nome do estado\n'
                              
                    if not inv.partner_shipping_id.l10n_br_city_id:
                        strErro += u'Destinatário / Endereço - Município\n'
                    else:
                        if not inv.partner_shipping_id.l10n_br_city_id.name:
                            strErro += u'Destinatário / Endereço de Entrega - Nome do município\n'
                        if not inv.partner_shipping_id.l10n_br_city_id.ibge_code:
                            strErro += u'Destinatário / Endereço de Entrega - Código do IBGE do município\n'
                            
                    if not inv.partner_shipping_id.country_id:
                        strErro += u'Destinatário / Endereço de Entrega - País\n'
                    else:
                        if not inv.partner_shipping_id.country_id.name:
                            strErro += u'Destinatário / Endereço de Entrega - Nome do país\n'
                        if not inv.partner_shipping_id.country_id.bc_code:
                            strErro += u'Destinatário / Endereço de Entrega - Código do BC do país\n'
                    
            #produtos
            for inv_line in inv.invoice_line:
                if inv_line.product_id:
                    if not inv_line.product_id.default_code:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - Referência/Código do produto\n' % (inv_line.product_id.name, inv_line.quantity)
                    if not inv_line.product_id.name:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - Nome do produto\n' % (inv_line.product_id.name, inv_line.quantity) 
        
                    if not inv_line.cfop_id:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - CFOP\n' % (inv_line.product_id.name, inv_line.quantity)
                    else:
                        if not inv_line.cfop_id.code:
                            strErro += u'Produtos e Serviços: %s, Qtde: %s - Código do CFOP\n' % (inv_line.product_id.name, inv_line.quantity)
        
                    if not inv_line.uos_id:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - Unidade de medida\n' % (inv_line.product_id.name, inv_line.quantity)
                    
                    if not inv_line.quantity:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - Quantidade\n' % (inv_line.product_id.name, inv_line.quantity)
                    
                    if not inv_line.price_unit:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - Preco unitario\n' % (inv_line.product_id.name, inv_line.quantity)
                        
                    if not inv_line.icms_cst:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - CST do ICMS\n' % (inv_line.product_id.name, inv_line.quantity)
                        
                    if not inv_line.ipi_cst:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - CST do IPI\n' % (inv_line.product_id.name, inv_line.quantity)
                    
                    if not inv_line.pis_cst:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - CST do PIS\n' % (inv_line.product_id.name, inv_line.quantity)
                        
                    if not inv_line.cofins_cst:
                        strErro += u'Produtos e Serviços: %s, Qtde: %s - CST do COFINS\n' % (inv_line.product_id.name, inv_line.quantity)
                
        if strErro:
            raise osv.except_osv(_('Error !'), _("Error Validating NFE:\n '%s'") % (strErro, ))
        
        return True
        

    def nfe_export_txt(self, cr, uid, ids, nfe_environment='1', context=False):
        StrFile = ''
        StrNF = 'NOTA FISCAL|%s|\n' % len(ids)
        StrFile = StrNF
        
        for inv in self.browse(cr, uid, ids, context={'lang': 'pt_BR'}):
            #Endereço do company
            company_addr = self.pool.get('res.partner').address_get(cr, uid, [inv.company_id.partner_id.id], ['default'])
            company_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [company_addr['default']], context={'lang': 'pt_BR'})[0]
            #nfe_key = unicode(company_addr_default.state_id.ibge_code).strip().rjust(2, u'0')
            #nfe_key += unicode(datetime.strptime(inv.date_invoice, '%Y-%m-%d').strftime(u'%y%m')).strip().rjust(4, u'0')
            #nfe_key +=  re.sub('[%s]' % re.escape(string.punctuation), '', inv.company_id.partner_id.cnpj_cpf or '')
            #nfe_key += inv.fiscal_document_id.code
            #nfe_key += unicode(inv.document_serie_id.code).strip().rjust(3, u'0')
            #nfe_key += unicode(inv.internal_number).strip().rjust(9, u'0')
            #fe_key += unicode('1').strip().rjust(1, u'0') # Homologação
            #nfe_key += unicode(inv.internal_number).strip().rjust(8, u'0')
            #nfe_key += unicode(self.nfe_dv(nfe_key)).strip().rjust(1, u'0')

            StrA = 'A|%s|%s|\n' % ('2.00', '')

            StrFile += StrA
            
            StrRegB = {
                       'cUF': company_addr_default.state_id.ibge_code,
                       'cNF': '',
                       'NatOp': normalize('NFKD',unicode(inv.cfop_ids[0].small_name or '')).encode('ASCII','ignore'),
                       'intPag': '2', 
                       'mod': inv.fiscal_document_id.code,
                       'serie': inv.document_serie_id.code,
                       'nNF': inv.internal_number or '',
                       'dEmi': inv.date_invoice or '',
                       'dSaiEnt': inv.date_invoice or '',
                       'hSaiEnt': '',
                       'tpNF': '',
                       'cMunFG': ('%s%s') % (company_addr_default.state_id.ibge_code, company_addr_default.l10n_br_city_id.ibge_code),
                       'TpImp': '1',
                       'TpEmis': '1',
                       'cDV': '',
                       'tpAmb': nfe_environment,
                       'finNFe': '1',
                       'procEmi': '0',
                       'VerProc': '2.2.1',
                       'dhCont': '',
                       'xJust': '',
                       }

            if inv.cfop_ids[0].type in ("input"):
                StrRegB['tpNF'] = '0'
            else:
                StrRegB['tpNF'] = '1' 

            StrB = 'B|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegB['cUF'], StrRegB['cNF'], StrRegB['NatOp'], StrRegB['intPag'], 
                                                                                 StrRegB['mod'], StrRegB['serie'], StrRegB['nNF'], StrRegB['dEmi'], StrRegB['dSaiEnt'],
                                                                                 StrRegB['hSaiEnt'], StrRegB['tpNF'], StrRegB['cMunFG'], StrRegB['TpImp'], StrRegB['TpEmis'],
                                                                                 StrRegB['cDV'], StrRegB['tpAmb'], StrRegB['finNFe'], StrRegB['procEmi'], StrRegB['VerProc'], 
                                                                                 StrRegB['dhCont'], StrRegB['xJust'])
            StrFile += StrB
            
            StrRegC = {
                       'XNome': normalize('NFKD',unicode(inv.company_id.partner_id.legal_name or '')).encode('ASCII','ignore'), 
                       'XFant': normalize('NFKD',unicode(inv.company_id.partner_id.name or '')).encode('ASCII','ignore'),
                       'IE': re.sub('[%s]' % re.escape(string.punctuation), '', inv.company_id.partner_id.inscr_est or ''),
                       'IEST': '',
                       'IM': re.sub('[%s]' % re.escape(string.punctuation), '', inv.company_id.partner_id.inscr_mun or ''),
                       'CNAE': re.sub('[%s]' % re.escape(string.punctuation), '', inv.company_id.cnae_main_id.code or ''),
                       'CRT': inv.company_id.fiscal_type or '',
                       }
            
            #TODO - Verificar, pois quando e informado do CNAE ele exige que a inscricao municipal, parece um bug do emissor da NFE
            if not inv.company_id.partner_id.inscr_mun:
                StrRegC['CNAE'] = ''
            
            StrC = 'C|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegC['XNome'], StrRegC['XFant'], StrRegC['IE'], StrRegC['IEST'], 
                                                StrRegC['IM'],StrRegC['CNAE'],StrRegC['CRT'])

            StrFile += StrC

            if inv.company_id.partner_id.tipo_pessoa == 'J':
                StrC02 = 'C02|%s|\n' % (re.sub('[%s]' % re.escape(string.punctuation), '', inv.company_id.partner_id.cnpj_cpf or ''))
            else:
                StrC02 = 'C02a|%s|\n' % (re.sub('[%s]' % re.escape(string.punctuation), '', inv.company_id.partner_id.cnpj_cpf or ''))

            StrFile += StrC02

            address_company_bc_code = ''
            if company_addr_default.country_id.bc_code:
                address_company_bc_code = company_addr_default.country_id.bc_code[1:]

            StrRegC05 = {
                       'XLgr': normalize('NFKD',unicode(company_addr_default.street or '')).encode('ASCII','ignore'), 
                       'Nro': company_addr_default.number or '',
                       'Cpl': normalize('NFKD',unicode(company_addr_default.street2 or '')).encode('ASCII','ignore'),
                       'Bairro': normalize('NFKD',unicode(company_addr_default.district or 'Sem Bairro')).encode('ASCII','ignore'),
                       'CMun': '%s%s' % (company_addr_default.state_id.ibge_code, company_addr_default.l10n_br_city_id.ibge_code),
                       'XMun':  normalize('NFKD',unicode(company_addr_default.l10n_br_city_id.name or '')).encode('ASCII','ignore'),
                       'UF': company_addr_default.state_id.code or '',
                       'CEP': re.sub('[%s]' %  re.escape(string.punctuation), '', str(company_addr_default.zip or '').replace(' ','')),
                       'cPais': address_company_bc_code or '',
                       'xPais': normalize('NFKD',unicode(company_addr_default.country_id.name or '')).encode('ASCII','ignore'),
                       'fone': re.sub('[%s]' % re.escape(string.punctuation), '', str(company_addr_default.phone or '').replace(' ','')),
                       }

            StrC05 = 'C05|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegC05['XLgr'], StrRegC05['Nro'], StrRegC05['Cpl'], StrRegC05['Bairro'],
                                                                  StrRegC05['CMun'], StrRegC05['XMun'], StrRegC05['UF'], StrRegC05['CEP'],
                                                                  StrRegC05['cPais'], StrRegC05['xPais'], StrRegC05['fone'])

            StrFile += StrC05

            address_invoice_bc_code = ''
            address_invoice_state_code = ''
            address_invoice_city = ''
            UFEmbarq = ''
            XLocEmbarq = ''
            address_invoice_cep = ''
            if inv.address_invoice_id.country_id.bc_code:
                address_invoice_bc_code = inv.address_invoice_id.country_id.bc_code[1:]
                
            if inv.address_invoice_id.country_id.id != company_addr_default.country_id.id:
                address_invoice_state_code = 'EX'
                address_invoice_city = 'Exterior'
                UFEmbarq = company_addr_default.state_id.code
                XLocEmbarq = company_addr_default.city
                address_invoice_cep = ''
            else:
                address_invoice_state_code = inv.address_invoice_id.state_id.code
                address_invoice_city = normalize('NFKD',unicode(inv.address_invoice_id.l10n_br_city_id.name or '')).encode('ASCII','ignore')
                address_invoice_cep = re.sub('[%s]' % re.escape(string.punctuation), '', str(inv.address_invoice_id.zip or '').replace(' ',''))
            
            # Se o ambiente for de teste deve ser escrito na razão do destinatário
            if nfe_environment == '2': 
                xNome = 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL'
            else:
                xNome = normalize('NFKD', unicode(inv.partner_id.legal_name or '')).encode('ASCII', 'ignore')

            StrRegE = {
                       'xNome': xNome, 
                       'IE': re.sub('[%s]' % re.escape(string.punctuation), '', inv.partner_id.inscr_est or ''),
                       'ISUF': '',
                       'email': inv.partner_id.email or '',
                       }
            
            StrE = 'E|%s|%s|%s|%s|\n' % (StrRegE['xNome'], StrRegE['IE'], StrRegE['ISUF'], StrRegE['email'])

            StrFile += StrE

            if inv.partner_id.tipo_pessoa == 'J':
                StrE0 = 'E02|%s|\n' % (re.sub('[%s]' % re.escape(string.punctuation), '', inv.partner_id.cnpj_cpf or ''))
            else:
                StrE0 = 'E03|%s|\n' % (re.sub('[%s]' % re.escape(string.punctuation), '', inv.partner_id.cnpj_cpf or ''))

            StrFile += StrE0

            StrRegE05 = {
                       'xLgr': normalize('NFKD',unicode(inv.address_invoice_id.street or '')).encode('ASCII','ignore'),
                       'nro': normalize('NFKD',unicode(inv.address_invoice_id.number or '')).encode('ASCII','ignore'),
                       'xCpl': re.sub('[%s]' % re.escape(string.punctuation), '', normalize('NFKD',unicode(inv.address_invoice_id.street2 or '' )).encode('ASCII','ignore')),
                       'xBairro': normalize('NFKD',unicode(inv.address_invoice_id.district or 'Sem Bairro')).encode('ASCII','ignore'),
                       'cMun': ('%s%s') % (inv.address_invoice_id.state_id.ibge_code, inv.address_invoice_id.l10n_br_city_id.ibge_code),
                       'xMun': address_invoice_city,
                       'UF': address_invoice_state_code,
                       'CEP': address_invoice_cep,
                       'cPais': address_invoice_bc_code,
                       'xPais': normalize('NFKD',unicode(inv.address_invoice_id.country_id.name or '')).encode('ASCII','ignore'),
                       'fone': re.sub('[%s]' % re.escape(string.punctuation), '', str(inv.address_invoice_id.phone or '').replace(' ','')),
                       }

            StrE05 = 'E05|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegE05['xLgr'], StrRegE05['nro'], StrRegE05['xCpl'], StrRegE05['xBairro'],
                                                           StrRegE05['cMun'], StrRegE05['xMun'], StrRegE05['UF'], StrRegE05['CEP'],
                                                           StrRegE05['cPais'],StrRegE05['xPais'], StrRegE05['fone'],)
            
            StrFile += StrE05
            
            if inv.partner_shipping_id:
                
                if inv.address_invoice_id != inv.partner_shipping_id: 
            
                    StrRegG = {
                               'XLgr': normalize('NFKD',unicode(inv.partner_shipping_id.street or '',)).encode('ASCII','ignore'),
                               'Nro': normalize('NFKD',unicode(inv.partner_shipping_id.number or '')).encode('ASCII','ignore'),
                               'XCpl': re.sub('[%s]' % re.escape(string.punctuation), '', normalize('NFKD',unicode(inv.partner_shipping_id.street2 or '' )).encode('ASCII','ignore')),
                               'XBairro': re.sub('[%s]' % re.escape(string.punctuation), '', normalize('NFKD',unicode(inv.partner_shipping_id.district or 'Sem Bairro' )).encode('ASCII','ignore')),
                               'CMun': ('%s%s') % (inv.partner_shipping_id.state_id.ibge_code, inv.partner_shipping_id.l10n_br_city_id.ibge_code),
                               'XMun': normalize('NFKD',unicode(inv.partner_shipping_id.l10n_br_city_id.name or '')).encode('ASCII','ignore'),
                               'UF': inv.address_invoice_id.state_id.code,
                             }
          
                    StrG = 'G|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegG['XLgr'],StrRegG['Nro'],StrRegG['XCpl'],StrRegG['XBairro'],StrRegG['CMun'],StrRegG['XMun'],StrRegG['UF'])
                    StrFile += StrG
                    
                    if inv.partner_id.tipo_pessoa == 'J':
                        StrG0 = 'G02|%s|\n' % (re.sub('[%s]' % re.escape(string.punctuation), '', inv.partner_id.cnpj_cpf or ''))
                    else:
                        StrG0 = 'G02a|%s|\n' % (re.sub('[%s]' % re.escape(string.punctuation), '', inv.partner_id.cnpj_cpf or ''))
        
                    StrFile += StrG0
            
            i = 0
            for inv_line in inv.invoice_line:
                i += 1
            
                StrH = 'H|%s||\n' % (i)
            
                StrFile += StrH
            
                StrRegI = {
                       'CProd': normalize('NFKD',unicode(inv_line.product_id.code or '',)).encode('ASCII','ignore'),
                       'CEAN': inv_line.product_id.ean13 or '',
                       'XProd': normalize('NFKD',unicode(inv_line.product_id.name or '')).encode('ASCII','ignore'),
                       'NCM': re.sub('[%s]' % re.escape(string.punctuation), '', inv_line.product_id.property_fiscal_classification.name or ''),
                       'EXTIPI': '',
                       'CFOP': inv_line.cfop_id.code,
                       'UCom': normalize('NFKD',unicode(inv_line.uos_id.name or '',)).encode('ASCII','ignore'),
                       'QCom': str("%.4f" % inv_line.quantity),
                       'VUnCom': str("%.2f" % (inv_line.price_unit * (1-(inv_line.discount or 0.0)/100.0))),
                       'VProd': str("%.2f" % inv_line.price_total),
                       'CEANTrib': inv_line.product_id.ean13 or '',
                       'UTrib': inv_line.uos_id.name,
                       'QTrib': str("%.4f" % inv_line.quantity),
                       'VUnTrib': str("%.2f" % inv_line.price_unit),
                       'VFrete': '',
                       'VSeg': '',
                       'VDesc': '',
                       'vOutro': '',
                       'indTot': '1',
                       'xPed': '',
                       'nItemPed': '',
                       }

                if inv_line.product_id.code:
                    StrRegI['CProd'] = inv_line.product_id.code
                else:
                    StrRegI['CProd'] = unicode(i).strip().rjust(4, u'0')

                #No OpenERP já traz o valor unitário como desconto
                #if inv_line.discount > 0:
                #    StrRegI['VDesc'] = str("%.2f" % (inv_line.quantity * (inv_line.price_unit * (1-(inv_line.discount or 0.0)/100.0))))

                StrI = 'I|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegI['CProd'], StrRegI['CEAN'], StrRegI['XProd'], StrRegI['NCM'],
                                                                                          StrRegI['EXTIPI'], StrRegI['CFOP'], StrRegI['UCom'], StrRegI['QCom'], 
                                                                                          StrRegI['VUnCom'], StrRegI['VProd'], StrRegI['CEANTrib'], StrRegI['UTrib'],
                                                                                          StrRegI['QTrib'], StrRegI['VUnTrib'], StrRegI['VFrete'], StrRegI['VSeg'],
                                                                                          StrRegI['VDesc'], StrRegI['vOutro'], StrRegI['indTot'], StrRegI['xPed'],
                                                                                          StrRegI['nItemPed'])
                
                StrFile += StrI
                
                StrM = 'M|\n'
                
                StrFile += StrM
                
                StrN = 'N|\n'
         
                StrFile += StrN

                #TODO - Fazer alteração para cada tipo de cst
                if inv_line.icms_cst in ('00'):
                    
                    StrRegN02 = {
                       'Orig': inv_line.product_id.origin or '0',
                       'CST': inv_line.icms_cst,
                       'ModBC': '0',
                       'VBC': str("%.2f" % inv_line.icms_base),
                       'PICMS': str("%.2f" % inv_line.icms_percent),
                       'VICMS': str("%.2f" % inv_line.icms_value),
                       }
                
                    StrN02 = 'N02|%s|%s|%s|%s|%s|%s|\n' % (StrRegN02['Orig'], StrRegN02['CST'], StrRegN02['ModBC'], StrRegN02['VBC'], StrRegN02['PICMS'],
                                                     StrRegN02['VICMS'])
                    
                    StrFile += StrN02
                
                if inv_line.icms_cst in ('20'):

                    StrRegN04 = {
                       'Orig': inv_line.product_id.origin or '0',
                       'CST': inv_line.icms_cst,
                       'ModBC': '0',
                       'PRedBC': str("%.2f" % inv_line.icms_percent_reduction),
                       'VBC': str("%.2f" % inv_line.icms_base),
                       'PICMS': str("%.2f" % inv_line.icms_percent),
                       'VICMS': str("%.2f" % inv_line.icms_value),
                       }
                
                    StrN04 = 'N04|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegN04['Orig'], StrRegN04['CST'], StrRegN04['ModBC'], StrRegN04['PRedBC'], StrRegN04['VBC'], StrRegN04['PICMS'],
                                                              StrRegN04['VICMS'])
                    StrFile += StrN04
                
                if inv_line.icms_cst in ('10'):
                    StrRegN03 = {
                       'Orig': inv_line.product_id.origin or '0',
                       'CST': inv_line.icms_cst,
                       'ModBC': '0',
                       'VBC': str("%.2f" % inv_line.icms_base),
                       'PICMS': str("%.2f" % inv_line.icms_percent),
                       'VICMS': str("%.2f" % inv_line.icms_value),
                       'ModBCST': '4', #TODO
                       'PMVAST': str("%.2f" % inv_line.icms_st_mva) or '',
                       'PRedBCST': '',
                       'VBCST': str("%.2f" % inv_line.icms_st_base),
                       'PICMSST': str("%.2f" % inv_line.icms_st_percent),
                       'VICMSST': str("%.2f" % inv_line.icms_st_value),
                       }

                    StrN03 = 'N03|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegN03['Orig'], StrRegN03['CST'], StrRegN03['ModBC'], StrRegN03['VBC'], StrRegN03['PICMS'],
                    StrRegN03['VICMS'], StrRegN03['ModBCST'], StrRegN03['PMVAST'], StrRegN03['PRedBCST'], StrRegN03['VBCST'],
                    StrRegN03['PICMSST'], StrRegN03['VICMSST'])
                    StrFile += StrN03
                    
                if inv_line.icms_cst in ('40', '41', '50', '51'):
                    StrRegN06 = {
                       'Orig': inv_line.product_id.origin or '0',
                       'CST': inv_line.icms_cst,
                       'vICMS': str("%.2f" % inv_line.icms_value),
                       'motDesICMS': '9', #FIXME
                       }
                
                    StrN06 = 'N06|%s|%s|%s|%s|\n' % (StrRegN06['Orig'], StrRegN06['CST'], StrRegN06['vICMS'], StrRegN06['motDesICMS'])
                    
                    StrFile += StrN06
                
                if inv_line.icms_cst in ('60'):                    
                    StrRegN08 = {
                       'Orig': inv_line.product_id.origin or '0',
                       'CST': inv_line.icms_cst,
                       'VBCST': str("%.2f" % 0.00),
                       'VICMSST': str("%.2f" % 0.00),
                       }

                    StrN08 = 'N08|%s|%s|%s|%s|\n' % (StrRegN08['Orig'], StrRegN08['CST'], StrRegN08['VBCST'], StrRegN08['VICMSST'])
                    
                    StrFile += StrN08
                    
                if inv_line.icms_cst in ('70'):
                    StrRegN09 = {
                       'Orig': inv_line.product_id.origin or '0',
                       'CST': inv_line.icms_cst,
                       'ModBC': '0',
                       'PRedBC': str("%.2f" % inv_line.icms_percent_reduction),
                       'VBC': str("%.2f" % inv_line.icms_base),
                       'PICMS': str("%.2f" % inv_line.icms_percent),
                       'VICMS': str("%.2f" % inv_line.icms_value),
                       'ModBCST': '4', #TODO
                       'PMVAST': str("%.2f" % inv_line.icms_st_mva) or '',
                       'PRedBCST': '',
                       'VBCST': str("%.2f" % inv_line.icms_st_base),
                       'PICMSST': str("%.2f" % inv_line.icms_st_percent),
                       'VICMSST': str("%.2f" % inv_line.icms_st_value),
                       }
                
                    StrN09 = 'N09|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegN09['Orig'], StrRegN09['CST'], StrRegN09['ModBC'], StrRegN09['PRedBC'], StrRegN09['VBC'], StrRegN09['PICMS'], StrRegN09['VICMS'], StrRegN09['ModBCST'], StrRegN09['PMVAST'], StrRegN09['PRedBCST'], StrRegN09['VBCST'], StrRegN09['PICMSST'], StrRegN09['VICMSST'])

                    StrFile += StrN09
                    
                if inv_line.icms_cst in ('90', '900'):
                    StrRegN10h = {
                                  'Orig': inv_line.product_id.origin or '0',
                                  'CSOSN': inv_line.icms_cst,
                                  'modBC': '0',
                                  'vBC': str("%.2f" % 0.00),
                                  'pRedBC': '',
                                  'pICMS': str("%.2f" % 0.00),
                                  'vICMS': str("%.2f" % 0.00),
                                  'modBCST': '',
                                  'pMVAST': '',
                                  'pRedBCST': '',
                                  'vBCST': '',
                                  'pICMSST': '',
                                  'vICMSST': '',
                                  'pCredSN': str("%.2f" % 0.00),
                                  'vCredICMSSN': str("%.2f" % 0.00),
                                  }
                                    
                    StrN10h = 'N10h|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegN10h['Orig'], 
                                                                                        StrRegN10h['CSOSN'], 
                                                                                        StrRegN10h['modBC'],
                                                                                        StrRegN10h['vBC'],
                                                                                        StrRegN10h['pRedBC'],
                                                                                        StrRegN10h['pICMS'],
                                                                                        StrRegN10h['vICMS'],
                                                                                        StrRegN10h['modBCST'],
                                                                                        StrRegN10h['pMVAST'],
                                                                                        StrRegN10h['pRedBCST'],
                                                                                        StrRegN10h['vBCST'],
                                                                                        StrRegN10h['pICMSST'],
                                                                                        StrRegN10h['vICMSST'],
                                                                                        StrRegN10h['pCredSN'],
                                                                                        StrRegN10h['vCredICMSSN'])

                    StrFile += StrN10h

                StrRegO = {
                       'ClEnq': '',
                       'CNPJProd': '',
                       'CSelo': '',
                       'QSelo': '',
                       'CEnq': '999',
                }
                
                StrO = 'O|%s|%s|%s|%s|%s|\n' % (StrRegO['ClEnq'], StrRegO['CNPJProd'], StrRegO['CSelo'], StrRegO['QSelo'], StrRegO['CEnq']) 
                
                StrFile += StrO

                if inv_line.ipi_cst in ('50', '51', '52') and inv_line.ipi_percent > 0:
                    StrRegO07 = {
                       'CST': inv_line.ipi_cst,
                       'VIPI': str("%.2f" % inv_line.ipi_value),
                    }
                    
                    StrO07 = 'O07|%s|%s|\n' % (StrRegO07['CST'], StrRegO07['VIPI'])
                    
                    StrFile += StrO07 

                    if inv_line.ipi_type == 'percent' or '':
                        StrRegO10 = {
                           'VBC': str("%.2f" % inv_line.ipi_base),
                           'PIPI': str("%.2f" % inv_line.ipi_percent),
                        }
                        StrO1 = 'O10|%s|%s|\n' % (StrRegO10['VBC'], StrRegO10['PIPI'])
                    
                    if inv_line.ipi_type == 'quantity':
                        pesol = 0
                        if inv_line.product_id:
                            pesol = inv_line.product_id.weight_net
                        StrRegO11 = {
                           'QUnid': str("%.4f" % (inv_line.quantity * pesol)),
                           'VUnid': str("%.4f" % inv_line.ipi_percent),
                        }
                        StrO1 = 'O11|%s|%s|\n' % (StrRegO11['QUnid'], StrRegO11['VUnid'])
                    
                    StrFile += StrO1
                
                if inv_line.ipi_cst in ('99'):
                    StrRegO07 = {
                                 'CST': inv_line.ipi_cst,
                                 'VIPI': str("%.2f" % inv_line.ipi_value),
                                 }
                    
                    StrO07 = ('O07|%s|%s|\n') % (StrRegO07['CST'], StrRegO07['VIPI'])
                    StrFile += StrO07
                    
                    StrRegO10 = {
                                 'VBC': str("%.2f" % inv_line.ipi_base),
                                 'PIPI': str("%.2f" % inv_line.ipi_percent),
                                 }
                    
                    StrO10 = ('O10|%s|%s|\n') % (StrRegO10['VBC'], StrRegO10['PIPI'])
                    StrFile += StrO10
                    
                if inv_line.ipi_percent == 0 and not inv_line.ipi_cst in ('99'):
                    StrO1 = 'O08|%s|\n' % inv_line.ipi_cst
                    StrFile += StrO1
              
                StrRegP = {
                       'VBC': str("%.2f" % inv_line.ii_base),
                       'VDespAdu': str("%.2f" % inv_line.ii_customhouse_charges),
                       'VII': str("%.2f" % inv_line.ii_value),
                       'VIOF': str("%.2f" % inv_line.ii_iof),
                }

                StrP = ('P|%s|%s|%s|%s|\n') % (StrRegP['VBC'], StrRegP['VDespAdu'], StrRegP['VII'], StrRegP['VIOF'])
                StrFile += StrP
                
                StrQ = 'Q|\n'
                StrFile += StrQ
                    
                if inv_line.pis_cst in ('01') and inv_line.pis_percent > 0:
                    StrRegQ02 = {
                                 'CST': inv_line.pis_cst,
                                 'VBC': str("%.2f" % inv_line.pis_base),
                                 'PPIS': str("%.2f" % inv_line.pis_percent),
                                 'VPIS': str("%.2f" % inv_line.pis_value),
                                 }
                    
                    StrQ02 = ('Q02|%s|%s|%s|%s|\n') % (StrRegQ02['CST'], 
                                                       StrRegQ02['VBC'], 
                                                       StrRegQ02['PPIS'], 
                                                       StrRegQ02['VPIS'])
                    
                    StrFile += StrQ02
                    
                if inv_line.pis_cst in ('99'):
                    StrRegQ05 = {
                                 'CST': inv_line.pis_cst,
                                 'VPIS': str("%.2f" % inv_line.pis_value),
                                 }
                    
                    StrQ05 = ('Q05|%s|%s|\n') % (StrRegQ05['CST'], StrRegQ05['VPIS'])
                    StrFile += StrQ05
                    
                    StrRegQ07 = {
                                 'VBC': str("%.2f" % inv_line.pis_base),
                                 'PPIS': str("%.2f" % inv_line.pis_percent),
                                 }
                    
                    StrQ07 = ('Q07|%s|%s|\n') % (StrRegQ07['VBC'], StrRegQ07['PPIS'])
                    StrFile += StrQ07
                    
                if inv_line.pis_percent == 0 and not inv_line.pis_cst in ('99'):
                    StrQ02 = 'Q04|%s|\n' % inv_line.pis_cst
                    StrFile += StrQ02
                
                StrQ = 'S|\n'
                
                StrFile += StrQ

                if inv_line.cofins_cst in ('01') and inv_line.cofins_percent > 0:
                    StrRegS02 = {
                       'CST': inv_line.cofins_cst,
                       'VBC': str("%.2f" % inv_line.cofins_base),
                       'PCOFINS': str("%.2f" % inv_line.cofins_percent),
                       'VCOFINS': str("%.2f" % inv_line.cofins_value),
                    }

                    StrS02 = ('S02|%s|%s|%s|%s|\n') % (StrRegS02['CST'], StrRegS02['VBC'], StrRegS02['PCOFINS'], StrRegS02['VCOFINS'])
                    StrFile += StrS02
                    
                if inv_line.cofins_cst in ('99'):
                    StrRegS05 = {
                                 'CST': inv_line.cofins_cst,
                                 'VCOFINS': str("%.2f" % inv_line.cofins_value),
                                 }
                    
                    StrS05 = ('S05|%s|%s|\n') % (StrRegS05['CST'], StrRegS05['VCOFINS'])
                    StrFile += StrS05
                    
                    StrRegS07 = {
                                 'VBC': str("%.2f" % inv_line.cofins_base),
                                 'PCOFINS': str("%.2f" % inv_line.cofins_percent),
                                 }
                    
                    StrS07 = ('S07|%s|%s|\n') % (StrRegS07['VBC'], StrRegS07['PCOFINS'])
                    StrFile += StrS07
                        
            if inv_line.cofins_percent == 0 and not inv_line.cofins_cst in ('99'):
                StrS02 = 'S04|%s|\n' % inv_line.cofins_cst
                StrFile += StrS02
                
            StrW = 'W|\n'
            
            StrFile += StrW

            StrRegW02 = {
                         'vBC': str("%.2f" % inv.icms_base),
                         'vICMS': str("%.2f" % inv.icms_value),
                         'vBCST': str("%.2f" % inv.icms_st_base),
                         'vST': str("%.2f" % inv.icms_st_value),
                         'vProd': str("%.2f" % inv.amount_untaxed),
                         'vFrete': str("%.2f" % inv.amount_freight),
                         'vSeg': str("%.2f" % inv.amount_insurance),
                         'vDesc': '0.00',
                         'vII': str("%.2f" % inv.ii_value),
                         'vIPI': str("%.2f" % inv.ipi_value),
                         'vPIS': str("%.2f" % inv.pis_value),
                         'vCOFINS': str("%.2f" % inv.cofins_value),
                         'vOutro': str("%.2f" % inv.amount_costs),
                         'vNF': str("%.2f" % inv.amount_total),
                         }
            
            StrW02 = 'W02|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n' % (StrRegW02['vBC'], StrRegW02['vICMS'], StrRegW02['vBCST'], StrRegW02['vST'], StrRegW02['vProd'],
                                                                         StrRegW02['vFrete'], StrRegW02['vSeg'], StrRegW02['vDesc'], StrRegW02['vII'], StrRegW02['vIPI'],
                                                                         StrRegW02['vPIS'], StrRegW02['vCOFINS'], StrRegW02['vOutro'], StrRegW02['vNF'])
            
            StrFile += StrW02
            
            # Modo do Frete: 0- Por conta do emitente; 1- Por conta do destinatário/remetente; 2- Por conta de terceiros; 9- Sem frete (v2.0)
            if not inv.incoterm:
                StrRegX0 = '9'
            else:
                StrRegX0 = inv.incoterm.freight_responsibility                      

            StrX = 'X|%s|\n' % (StrRegX0)
            
            StrFile += StrX
            
            StrRegX03 = {
                      'XNome': '',
                      'IE': '',
                      'XEnder': '',
                      'UF': '',
                      'XMun': '',
                      }
            
            StrX0 = ''
            
            if inv.carrier_id:            
            
                #Endereço da transportadora
                carrier_addr = self.pool.get('res.partner').address_get(cr, uid, [inv.carrier_id.partner_id.id], ['default'])
                carrier_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [carrier_addr['default']])[0]
                
                if inv.carrier_id.partner_id.legal_name:
                    StrRegX03['XNome'] = normalize('NFKD', unicode(inv.carrier_id.partner_id.legal_name or '')).encode('ASCII', 'ignore')
                else:
                    StrRegX03['XNome'] = normalize('NFKD', unicode(inv.carrier_id.partner_id.name or '')).encode('ASCII', 'ignore')
                
                StrRegX03['IE'] = inv.carrier_id.partner_id.inscr_est or ''
                StrRegX03['XEnder'] = normalize('NFKD', unicode(carrier_addr_default.street or '')).encode('ASCII', 'ignore')
                StrRegX03['UF'] = carrier_addr_default.state_id.code or ''
                
                if carrier_addr_default.l10n_br_city_id:
                    StrRegX03['XMun'] = normalize('NFKD', unicode(carrier_addr_default.l10n_br_city_id.name or '')).encode('ASCII', 'ignore')
                
                if inv.carrier_id.partner_id.tipo_pessoa == 'J':
                    StrX0 = 'X04|%s|\n' %  (re.sub('[%s]' % re.escape(string.punctuation), '', inv.carrier_id.partner_id.cnpj_cpf or ''))
                else:
                    StrX0 = 'X05|%s|\n' %  (re.sub('[%s]' % re.escape(string.punctuation), '', inv.carrier_id.partner_id.cnpj_cpf or ''))

            StrX03 = 'X03|%s|%s|%s|%s|%s|\n' % (StrRegX03['XNome'], StrRegX03['IE'], StrRegX03['XEnder'], StrRegX03['UF'], StrRegX03['XMun'])

            StrFile += StrX03
            StrFile += StrX0

            StrRegX18 = {
                         'Placa': '',
                         'UF': '',
                         'RNTC': '',
                         }

            if inv.vehicle_id:
                StrRegX18['Placa'] = inv.vehicle_id.plate or ''
                StrRegX18['UF'] = inv.vehicle_id.plate.state_id.code or ''
                StrRegX18['RNTC'] = inv.vehicle_id.rntc_code or ''
                         

            StrX18 = 'X18|%s|%s|%s|\n' % (StrRegX18['Placa'], StrRegX18['UF'], StrRegX18['RNTC'])

            StrFile += StrX18

            StrRegX26 = {
                         'QVol': '',
                         'Esp': '', 
                         'Marca': '',
                         'NVol': '',
                         'PesoL': '',
                         'PesoB': '',
                         }

            if inv.number_of_packages:
                StrRegX26['QVol'] = inv.number_of_packages
                StrRegX26['Esp'] = 'Volume' #TODO
                StrRegX26['Marca']
                StrRegX26['NVol']
                StrRegX26['PesoL'] = str("%.3f" % inv.weight_net)
                StrRegX26['PesoB'] = str("%.3f" % inv.weight)

            StrX26 = 'X26|%s|%s|%s|%s|%s|%s|\n' % (StrRegX26['QVol'], StrRegX26['Esp'], StrRegX26['Marca'], StrRegX26['NVol'], StrRegX26['PesoL'], StrRegX26['PesoB'])

            StrFile += StrX26

            if inv.journal_id.revenue_expense:
            
                StrY = 'Y|\n'
                
                StrFile += StrY
                
                for line in inv.move_line_receivable_id:
                    StrRegY07 = {
                       'NDup': line.name,
                       'DVenc': line.date_maturity or inv.date_due or inv.date_invoice,
                       'VDup': str("%.2f" % line.debit),
                       }
                
                    StrY07 = 'Y07|%s|%s|%s|\n' % (StrRegY07['NDup'], StrRegY07['DVenc'], StrRegY07['VDup'])
                    
                    StrFile += StrY07
    
            StrRegZ = {
                       'InfAdFisco': '',
                       'InfCpl': normalize('NFKD',unicode(inv.comment or '')).encode('ASCII','ignore'),
                       }
            
            StrZ = 'Z|%s|%s|\n' % (StrRegZ['InfAdFisco'], StrRegZ['InfCpl'])

            StrFile += StrZ
            
            StrRegZA = {
                        'UFEmbarq': UFEmbarq,
                        'XLocEmbarq': XLocEmbarq,
                        }

            StrZA = 'ZA|%s|%s|\n' % (StrRegZA['UFEmbarq'], StrRegZA['XLocEmbarq'])
            StrFile += StrZA
            
            self.write(cr, uid, [inv.id], {'nfe_export_date': datetime.now()})

        return unicode(StrFile.encode('utf-8'), errors='replace')

    def nfe_export_xml(self, cr, uid, ids, nfe_environment='1', context=False):
                
        nfeProc = Element('nfeProc', {'versao': '2.00', 'xmlns': 'http://www.portalfiscal.inf.br/nfe' })
        
        for inv in self.browse(cr, uid, ids, context={'lang': 'pt_BR'}):
            
            #Endereço do company
            company_addr = self.pool.get('res.partner').address_get(cr, uid, [inv.company_id.partner_id.id], ['default'])
            company_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [company_addr['default']], context={'lang': 'pt_BR'})[0]
            
            #MontaChave da Nota Fiscal Eletronica
            nfe_key = unicode(company_addr_default.state_id.ibge_code).strip().rjust(2, u'0')
            nfe_key += unicode(datetime.strptime(inv.date_invoice, '%Y-%m-%d').strftime(u'%y%m')).strip().rjust(4, u'0')
            nfe_key +=  '08478495000170' # unicode(inv.company_id.partner_id.cnpj_cpf).strip().rjust(14, u'0')
            nfe_key += inv.fiscal_document_id.code
            nfe_key += unicode(inv.document_serie_id.code).strip().rjust(3, u'0')
            nfe_key += unicode(inv.internal_number).strip().rjust(9, u'0')
            nfe_key += unicode('1').strip().rjust(1, u'0') # Homologação
            nfe_key += unicode(inv.internal_number).strip().rjust(8, u'0')
            nfe_key += unicode(self.nfe_dv(nfe_key)).strip().rjust(1, u'0')
            
            NFe = SubElement(nfeProc, 'NFe', { 'xmlns': 'http://www.portalfiscal.inf.br/nfe' })
            
            infNFe = SubElement(NFe, 'infNFe', {'versao': '2.00', 'Id': nfe_key })

            # Dados da identificação da nota fiscal
            ide = SubElement(infNFe, 'ide')

            ide_cUF = SubElement(ide, 'cUF')
            ide_cUF.text = company_addr_default.state_id.ibge_code
            
            ide_cNF = SubElement(ide, 'cNF')
            ide_cNF.text = unicode(inv.internal_number).strip().rjust(8, u'0')
            
            ide_natOp = SubElement(ide, 'natOp')
            ide_natOp.text = inv.cfop_ids[0].name
            
            ide_indPag = SubElement(ide, 'indPag')
            ide_indPag.text = "2"
            
            ide_mod = SubElement(ide, 'mod')
            ide_mod.text = inv.fiscal_document_id.code 
            
            ide_serie = SubElement(ide, 'serie')
            ide_serie.text = inv.document_serie_id.code
            
            ide_nNF = SubElement(ide, 'nNF')
            ide_nNF.text = inv.internal_number
            
            ide_dEmi = SubElement(ide, 'dEmi')
            ide_dEmi.text = inv.date_invoice
            
            ide_dSaiEnt = SubElement(ide, 'dSaiEnt')
            ide_dSaiEnt.text = inv.date_invoice 
            
            ide_tpNF = SubElement(ide, 'tpNF')
            if inv.type in ("out_invoice", "in_refuld"): 
                ide_tpNF.text = '0'
            else:
                ide_tpNF.text = '1'
            
            ide_cMunFG = SubElement(ide, 'cMunFG')
            ide_cMunFG.text = ('%s%s') % (company_addr_default.state_id.ibge_code, company_addr_default.l10n_br_city_id.ibge_code)
            
            ide_tpImp = SubElement(ide, 'tpImp')
            ide_tpImp.text = "1"
            
            ide_tpEmis = SubElement(ide, 'tpEmis')
            ide_tpEmis.text = "1"
            
            ide_cDV = SubElement(ide, 'cDV')
            ide_cDV.text = self.nfe_dv(nfe_key)
            
            #Tipo de ambiente: 1 - Produção; 2 - Homologação
            ide_tpAmb = SubElement(ide, 'tpAmb')
            ide_tpAmb.text = "2"
            
            #Finalidade da emissão da NF-e: 1 - NFe normal 2 - NFe complementar 3 - NFe de ajuste
            ide_finNFe = SubElement(ide, 'finNFe')
            ide_finNFe.text = "1"
            
            ide_procEmi = SubElement(ide, 'procEmi')
            ide_procEmi.text = "0"
            
            ide_verProc = SubElement(ide, 'verProc')
            ide_verProc.text = "2.0.4"
            
            emit = SubElement(infNFe, 'emit')
            
            emit_CNPJ = SubElement(emit, 'CNPJ')
            emit_CNPJ.text = inv.company_id.partner_id.cnpj_cpf
            
            emit_xNome = SubElement(emit, 'xNome')
            emit_xNome.text = inv.company_id.partner_id.legal_name
            
            emit_xFant = SubElement(emit, 'xFant')
            emit_xFant.text = inv.company_id.partner_id.name
            
            enderEmit = SubElement(emit, 'enderEmit')
            
            enderEmit_xLgr = SubElement(enderEmit, 'xLgr')
            enderEmit_xLgr.text = company_addr_default.street
            
            enderEmit_nro = SubElement(enderEmit, 'nro')
            enderEmit_nro.text = company_addr_default.number
            
            enderEmit_xBairro = SubElement(enderEmit, 'xBairro')
            enderEmit_xBairro.text = company_addr_default.district
            
            enderEmit_cMun = SubElement(enderEmit, 'cMun')
            enderEmit_cMun.text = ('%s%s') % (company_addr_default.state_id.ibge_code, company_addr_default.l10n_br_city_id.ibge_code)
            
            enderEmit_xMun = SubElement(enderEmit, 'xMun')
            enderEmit_xMun.text = company_addr_default.l10n_br_city_id.name
            
            enderEmit_UF = SubElement(enderEmit, 'UF')
            enderEmit_UF.text = company_addr_default.state_id.code
            
            enderEmit_CEP = SubElement(enderEmit, 'CEP')
            enderEmit_CEP.text = company_addr_default.zip
            
            enderEmit_cPais = SubElement(enderEmit, 'cPais')
            enderEmit_cPais.text = company_addr_default.country_id.bc_code
            
            enderEmit_xPais = SubElement(enderEmit, 'xPais')
            enderEmit_xPais.text = company_addr_default.country_id.name
            
            enderEmit_fone = SubElement(enderEmit, 'fone')
            enderEmit_fone.text = company_addr_default.phone
            
            emit_IE = SubElement(emit, 'IE')
            emit_IE.text = inv.company_id.partner_id.inscr_est
            
            emit_IEST = SubElement(emit, 'IEST')
            emit_IEST.text = '0000000000' #FIXME
            
            emit_IM = SubElement(emit, 'IM')
            emit_IM.text = '0000000000' #FIXME
            
            emit_CNAE = SubElement(emit, 'CNAE')
            emit_CNAE.text = '0111301'  #FIXME
            
            emit_CRT = SubElement(emit, 'CRT')
            emit_CRT.text = '3'  #FIXME
            
            dest = SubElement(infNFe, 'dest')
            
            dest_CNPJ = SubElement(dest, 'CNPJ')
            dest_CNPJ.text = inv.partner_id.cnpj_cpf
            
            dest_xNome = SubElement(dest, 'xNome')
            dest_xNome.text = inv.partner_id.legal_name
            
            enderDest = SubElement(dest, 'enderDest')
            
            enderDest_xLgr = SubElement(enderDest, 'xLgr')
            enderDest_xLgr.text = inv.address_invoice_id.street
            
            enderDest_nro = SubElement(enderDest, 'nro')
            enderDest_nro.text = inv.address_invoice_id.number
            
            enderDest_xBairro = SubElement(enderDest, 'xBairro')
            enderDest_xBairro.text = inv.address_invoice_id.district
            
            enderDest_cMun = SubElement(enderDest, 'cMun')
            enderDest_cMun.text = ('%s%s') % (inv.address_invoice_id.state_id.ibge_code, inv.address_invoice_id.l10n_br_city_id.ibge_code)
            
            enderDest_xMun = SubElement(enderDest, 'xMun')
            enderDest_xMun.text = inv.address_invoice_id.l10n_br_city_id.name
            
            enderDest_UF = SubElement(enderDest, 'UF')
            enderDest_UF.text = inv.address_invoice_id.state_id.code
            
            enderDest_CEP = SubElement(enderDest, 'CEP')
            enderDest_CEP.text = inv.address_invoice_id.zip
            
            enderDest_cPais = SubElement(enderDest, 'cPais')
            enderDest_cPais.text = inv.address_invoice_id.country_id.bc_code
            
            enderDest_xPais = SubElement(enderDest, 'xPais')
            enderDest_xPais.text = inv.address_invoice_id.country_id.name
            
            enderDest_fone = SubElement(enderDest, 'fone')
            enderDest_fone.text = inv.address_invoice_id.phone
            
            dest_IE = SubElement(dest, 'IE')
            dest_IE.text = inv.partner_id.inscr_est
           
            i = 0 
            for inv_line in inv.invoice_line:
                i += 1
                det = SubElement(infNFe, 'det', {'nItem': str(i)})
                
                det_prod = SubElement(det, 'prod')
                
                prod_cProd = SubElement(det_prod, 'cProd')
                if inv_line.product_id.code:
                    prod_cProd.text = inv_line.product_id.code
                else:
                    prod_cProd.text = unicode(i).strip().rjust(4, u'0')
                
                prod_cEAN = SubElement(det_prod, 'cEAN')
                prod_cEAN.text = inv_line.product_id.ean13
                
                prod_xProd = SubElement(det_prod, 'xProd')
                prod_xProd.text = inv_line.product_id.name
                
                prod_NCM = SubElement(det_prod, 'NCM')
                prod_NCM.text = inv_line.product_id.property_fiscal_classification.name
                
                prod_CFOP = SubElement(det_prod, 'CFOP')
                prod_CFOP.text = inv_line.cfop_ids[0].code
                
                prod_uCom = SubElement(det_prod, 'uCom')
                prod_uCom.text = inv_line.uos_id.name
                
                prod_qCom = SubElement(det_prod, 'qCom')
                prod_qCom.text = str("%.4f" % inv_line.quantity)
                
                prod_vUnCom = SubElement(det_prod, 'vUnCom')
                prod_vUnCom.text = str("%.4f" % inv_line.price_unit)
                
                prod_vProd = SubElement(det_prod, 'vProd')
                prod_vProd.text = str("%.2f" % inv_line.price_subtotal)
                        
                prod_cEANTrib = SubElement(det_prod, 'cEANTrib')
                #prod_vProd.text(inv_line.total)
                
                prod_uTrib = SubElement(det_prod, 'uTrib')
                prod_uTrib.text = inv_line.uos_id.name
                
                prod_qTrib = SubElement(det_prod, 'qTrib')
                prod_qTrib.text = '0.0000'  #TODO
                
                prod_vUnTrib = SubElement(det_prod, 'vUnTrib')
                prod_vUnTrib.text = '0.00'  #TODO
                
                prod_vFrete = SubElement(det_prod, 'vFrete')
                prod_vFrete.text = '0.00'  #TODO - Valor do Frete
                
                prod_vSeg = SubElement(det_prod, 'vSeg')
                prod_vSeg.text = '0.00'  #TODO - Valor do seguro

                prod_vDesc = SubElement(det_prod, 'vDesc')
                prod_vDesc.text = str("%.2f" % inv_line.discount)  #TODO
                
                prod_vOutro = SubElement(det_prod, 'vOutro')
                prod_vOutro.text = '0.0000'  #TODO
                
                prod_indTot = SubElement(det_prod, 'indTot')
                prod_indTot.text = '1'  #TODO

                prod_imposto = SubElement(det, 'imposto')

                imposto_icms = SubElement(prod_imposto, 'ICMS' ) # + inv_line.icms_cst)
                
                imposto_icms_cst = SubElement(imposto_icms, 'ICMS%s' % (inv_line.icms_cst))
                
                icms_orig = SubElement(imposto_icms_cst, 'orig')
                icms_orig.text = inv_line.product_id.origin
                
                icms_CST = SubElement(imposto_icms_cst, 'CST')
                icms_CST.text = inv_line.icms_cst
                
                icms_modBC = SubElement(imposto_icms_cst, 'modBC')
                icms_modBC.text = '0' # TODO
                
                icms_vBC = SubElement(imposto_icms_cst, 'vBC')
                icms_vBC.text = str("%.2f" % inv_line.icms_base)
                
                icms_pICMS = SubElement(imposto_icms_cst, 'pICMS')
                icms_pICMS.text = str("%.2f" % inv_line.icms_percent)
                
                icms_vICMS = SubElement(imposto_icms_cst, 'vICMS')
                icms_vICMS.text = str("%.2f" % inv_line.icms_value)
                
                imposto_ipi = SubElement(prod_imposto, 'IPI')
                
                icms_cEnq = SubElement(imposto_ipi, 'cEnq')
                icms_cEnq.text = '999'
                
                #Imposto Não Tributado
                ipi_IPINT = SubElement(imposto_ipi, 'IPINT')
                
                ipi_CST = SubElement(ipi_IPINT, 'CST')
                ipi_CST.text = inv_line.ipi_cst
                
                imposto_pis = SubElement(prod_imposto, 'PIS')
                
                pis_PISAliq = SubElement(imposto_pis, 'PISAliq')
                
                pis_CST = SubElement(pis_PISAliq, 'CST')
                pis_CST.text = inv_line.pis_cst
                
                pis_vBC = SubElement(pis_PISAliq, 'vBC')
                pis_vBC.text = str("%.2f" % inv_line.pis_base)
                
                pis_pPIS = SubElement(pis_PISAliq, 'pPIS')
                pis_pPIS.text = str("%.2f" % inv_line.pis_percent)
                
                pis_vPIS = SubElement(pis_PISAliq, 'vPIS')
                pis_vPIS.text = str("%.2f" % inv_line.pis_value)
                
                imposto_cofins = SubElement(prod_imposto, 'COFINS')
                
                cofins_COFINSAliq = SubElement(imposto_cofins, 'COFINSAliq')
                
                cofins_CST = SubElement(cofins_COFINSAliq, 'CST')
                cofins_CST.text = inv_line.pis_cst
                
                cofins_vBC = SubElement(cofins_COFINSAliq, 'vBC')
                cofins_vBC.text = str("%.2f" % inv_line.cofins_base)
                
                cofins_pCOFINS = SubElement(cofins_COFINSAliq, 'pCOFINS')
                cofins_pCOFINS.text = str("%.2f" % inv_line.cofins_percent)
                
                cofins_vCOFINS = SubElement(cofins_COFINSAliq, 'vCOFINS')
                cofins_vCOFINS.text = str("%.2f" % inv_line.cofins_value)
                
            total = SubElement(infNFe, 'total')
            total_ICMSTot = SubElement(total, 'ICMSTot')
            
            ICMSTot_vBC = SubElement(total_ICMSTot, 'vBC')
            ICMSTot_vBC.text = str("%.2f" % inv.icms_base)
            
            ICMSTot_vICMS = SubElement(total_ICMSTot, 'vICMS')
            ICMSTot_vICMS.text = str("%.2f" % inv.icms_value)
            
            ICMSTot_vBCST = SubElement(total_ICMSTot, 'vBCST')
            ICMSTot_vBCST.text = '0.00' # TODO 
            
            ICMSTot_vST = SubElement(total_ICMSTot, 'vST')
            ICMSTot_vST.text = '0.00' # TODO
            
            ICMSTot_vProd = SubElement(total_ICMSTot, 'vProd')
            ICMSTot_vProd.text = str("%.2f" % inv.amount_untaxed)
            
            ICMSTot_vFrete = SubElement(total_ICMSTot, 'vFrete')
            ICMSTot_vFrete.text = '0.00' # TODO
            
            ICMSTot_vSeg = SubElement(total_ICMSTot, 'vSeg')
            ICMSTot_vSeg.text = str("%.2f" % inv.amount_insurance) 
            
            ICMSTot_vDesc = SubElement(total_ICMSTot, 'vDesc')
            ICMSTot_vDesc.text = '0.00' # TODO
            
            ICMSTot_II = SubElement(total_ICMSTot, 'vII')
            ICMSTot_II.text = '0.00' # TODO
            
            ICMSTot_vIPI = SubElement(total_ICMSTot, 'vIPI')
            ICMSTot_vIPI.text = str("%.2f" % inv.ipi_value)
            
            ICMSTot_vPIS = SubElement(total_ICMSTot, 'vPIS')
            ICMSTot_vPIS.text = str("%.2f" % inv.pis_value)
            
            ICMSTot_vCOFINS = SubElement(total_ICMSTot, 'vCOFINS')
            ICMSTot_vCOFINS.text = str("%.2f" % inv.cofins_value)
            
            ICMSTot_vOutro = SubElement(total_ICMSTot, 'vOutro')
            ICMSTot_vOutro.text = str("%.2f" % inv.amount_costs)
            
            ICMSTot_vNF = SubElement(total_ICMSTot, 'vNF')
            ICMSTot_vNF.text = str("%.2f" % inv.amount_total)
            
            
            transp = SubElement(infNFe, 'transp')
            
            # Modo do Frete: 0- Por conta do emitente; 1- Por conta do destinatário/remetente; 2- Por conta de terceiros; 9- Sem frete (v2.0)
            transp_modFrete = SubElement(transp, 'modFrete')
            transp_modFrete.text = '0' #TODO
            
            if inv.carrier_id:
                
                #Endereço do company
                carrier_addr = self.pool.get('res.partner').address_get(cr, uid, [inv.carrier_id.partner_id.id], ['default'])
                carrier_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [carrier_addr['default']])[0]
                
                transp_transporta = SubElement(transp, 'transporta')
                
                if inv.carrier_id.partner_id.tipo_pessoa == 'J':
                    transporta_CNPJ = SubElement(transp_transporta, 'CNPJ')
                    transporta_CNPJ.text = inv.carrier_id.partner_id.cnpj_cpf
                else:
                    transporta_CPF = SubElement(transp_transporta, 'CPF')
                    transporta_CPF.text = inv.carrier_id.partner_id.cnpj_cpf
                
                transporta_xNome = SubElement(transp_transporta, 'xNome')
                if inv.carrier_id.partner_id.legal_name:
                    transporta_xNome.text = inv.carrier_id.partner_id.legal_name
                else:
                    transporta_xNome.text = inv.carrier_id.partner_id.name
                
                transporta_IE = SubElement(transp_transporta, 'IE')
                transporta_IE.text = inv.carrier_id.partner_id.inscr_est
                
                transporta_xEnder = SubElement(transp_transporta, 'xEnder')
                transporta_xEnder.text = carrier_addr_default.street
                
                transporta_xMun = SubElement(transp_transporta, 'xMun')
                transporta_xMun.text = ('%s%s') % (carrier_addr_default.state_id.ibge_code, carrier_addr_default.l10n_br_city_id.ibge_code)
                
                transporta_UF = SubElement(transp_transporta, 'UF')
                transporta_UF.text = carrier_addr_default.state_id.code
                
            
            if inv.number_of_packages:
                transp_vol = SubElement(transp, 'vol')
            
                vol_qVol = SubElement(transp_vol, 'qVol')
                vol_qVol.text = inv.number_of_packages
                
                vol_esp = SubElement(transp_vol, 'esp')
                vol_esp.text = 'volume' #TODO
                
                vol_pesoL = SubElement(transp_vol, 'pesoL')
                vol_pesoL.text = inv.weight_net
                
                vol_pesoB = SubElement(transp_vol, 'pesoB')
                vol_pesoB.text = inv.weight
            
        xml_string = ElementTree.tostring(nfeProc, 'utf-8')
        return xml_string
    
    

    def _fiscal_position_map(self, cr, uid, ids, partner_id, partner_invoice_id, company_id, fiscal_operation_category_id):
        result = {'fiscal_operation_id': False, 
                  'fiscal_document_id': False, 
                  'document_serie_id': False,
                  'journal_id': False,}
        obj_rule = self.pool.get('account.fiscal.position.rule')
        obj_fo_category = self.pool.get('l10n_br_account.fiscal.operation.category')
        
        if not fiscal_operation_category_id:
            return result
        
        fiscal_result = obj_rule.fiscal_position_map(cr, uid, partner_id, partner_invoice_id, company_id, fiscal_operation_category_id, context={'use_domain': ('use_invoice', '=', True)})   
        result.update(fiscal_result)

        if result.get('fiscal_operation_id', False):
            obj_foperation = self.pool.get('l10n_br_account.fiscal.operation').browse(cr, uid, result['fiscal_operation_id'])
            result['fiscal_document_id'] = obj_foperation.fiscal_document_id.id
            
            obj_company = self.pool.get('res.company').browse(cr, uid, company_id)
            document_serie_id = [doc_serie for doc_serie in obj_company.document_serie_product_ids if doc_serie.fiscal_document_id.id == obj_foperation.fiscal_document_id.id and doc_serie.active]
            if not document_serie_id:
                raise osv.except_osv(_('Nenhuma série de documento fiscal !'),_("Empresa não tem uma série de documento fiscal cadastrada: '%s', você deve informar uma série no cadastro de empresas") % (obj_company.name,))
            else:
                result['document_serie_id'] = document_serie_id[0].id
            for inv in self.browse(cr, uid, ids):
                for line in inv.invoice_line:
                    line.cfop_id = obj_foperation.cfop_id.id
            
            if fiscal_operation_category_id:
                fo_category = obj_fo_category.browse(cr, uid, fiscal_operation_category_id)
                journal_ids = [journal for journal in fo_category.journal_ids if journal.company_id.id == company_id]
                if not journal_ids:
                    raise osv.except_osv(_('Nenhuma Diário !'),_("Categoria de operação fisca: '%s', não tem um diário contábil para a empresa %s") % (fo_category.name, obj_company.name))
                else:
                    result['journal_id'] = journal_ids[0].id
            
        return result

    def onchange_partner_id(self, cr, uid, ids, type, partner_id, date_invoice=False, 
                            payment_term=False, partner_bank_id=False, company_id=False, 
                            fiscal_operation_category_id=False):
        result = super(account_invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id, date_invoice, payment_term, partner_bank_id, company_id)
        partner_invoice_id = result['value'].get('address_invoice_id', False)
        fiscal_data = self._fiscal_position_map(cr, uid, ids, partner_id, partner_invoice_id, company_id, fiscal_operation_category_id)
        result['value'].update(fiscal_data)
        return result
    
    def onchange_company_id(self, cr, uid, ids, company_id, partner_id, type, invoice_line, currency_id, address_invoice_id, fiscal_operation_category_id=False):
        
        result = super(account_invoice, self).onchange_company_id(cr, uid, ids, company_id, partner_id, type, invoice_line, currency_id, address_invoice_id)
        fiscal_data = self._fiscal_position_map(cr, uid, ids, partner_id, address_invoice_id, company_id, fiscal_operation_category_id)
        result['value'].update(fiscal_data)
        return result

    def onchange_address_invoice_id(self, cr, uid, ids, company_id, partner_id, address_invoice_id, fiscal_operation_category_id=False):
        result = super(account_invoice, self).onchange_address_invoice_id(cr,uid,ids,company_id,partner_id,address_invoice_id)
        fiscal_data = self._fiscal_position_map(cr, uid, ids, partner_id, address_invoice_id, company_id, fiscal_operation_category_id)
        result['value'].update(fiscal_data)
        return result  

    def onchange_fiscal_operation_category_id(self, cr, uid, ids, partner_address_id=False, partner_id=False, company_id=False, fiscal_operation_category_id=False):
        result = {'value': {} }
        fiscal_data = self._fiscal_position_map(cr, uid, ids, partner_id, partner_address_id, company_id, fiscal_operation_category_id)
        result['value'].update(fiscal_data)
        return result

    def onchange_fiscal_operation_id(self, cr, uid, ids, partner_address_id=False, partner_id=False, company_id=False, fiscal_operation_category_id=False, fiscal_operation_id=False):
        result = {'value': {} }
        if not company_id or not fiscal_operation_category_id:
            return result
        fiscal_data = self._fiscal_position_map(cr, uid, ids, partner_id, partner_address_id, company_id, fiscal_operation_category_id)
        result['value'].update(fiscal_data)
       
        if fiscal_operation_id:
            obj_foperation = self.pool.get('l10n_br_account.fiscal.operation').browse(cr, uid, fiscal_operation_id)
            result['value']['fiscal_position'] = False
            result['fiscal_document_id'] = obj_foperation.fiscal_document_id.id
            del result['value']['fiscal_operation_id']

            for inv in self.browse(cr, uid, ids):
                for line in inv.invoice_line:
                    line.cfop_id = obj_foperation.cfop_id.id

        return result

account_invoice()


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, 
                        context=None, toolbar=False, submenu=False):
        
        result = super(account_invoice_line, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        
        if context is None:
            context = {}

        if view_type == 'form':
            
            eview = etree.fromstring(result['arch'])
            
            if 'type' in context.keys():

                operation_type = {'out_invoice': 'output', 
                                  'in_invoice': 'input', 
                                  'out_refund': 'input', 
                                  'in_refund': 'output'}

                cfops = eview.xpath("//field[@name='cfop_id']")
                for cfop_id in cfops:
                    cfop_id.set('domain', "[('type','=','%s')]" % (operation_type[context['type']],))
                    cfop_id.set('required', '1')

                fiscal_operation_categories = eview.xpath("//field[@name='fiscal_operation_category_id']")
                for fiscal_operation_category_id in fiscal_operation_categories:
                    fiscal_operation_category_id.set('domain', "[('fiscal_type','=','product'),('type','=','%s'),('use_invoice','=',True)]" % (operation_type[context['type']],))
                    fiscal_operation_category_id.set('required', '1')
                    
                fiscal_operations = eview.xpath("//field[@name='fiscal_operation_id']")
                for fiscal_operation_id in fiscal_operations:
                    fiscal_operation_id.set('domain', "[('fiscal_type','=','product'),('type','=','%s'),('fiscal_operation_category_id','=',fiscal_operation_category_id),('use_invoice','=',True)]" % (operation_type[context['type']],))
                    fiscal_operation_id.set('required', '1')
    
            
            if context.get('fiscal_type', False) == 'service':
                
                cfops = eview.xpath("//field[@name='cfop_id']")
                for cfop_id in cfops:
                    cfop_id.set('invisible', '1')
                    cfop_id.set('required', '0')
        
                if context['type'] in ('in_invoice', 'out_refund'):    
                    fiscal_operation_categories = eview.xpath("//field[@name='fiscal_operation_category_id']")
                    for fiscal_operation_category_id in fiscal_operation_categories:
                        fiscal_operation_category_id.set('domain', "[('fiscal_type','=','service'),('type','=','input'),('use_invoice','=',True)]")
                        fiscal_operation_category_id.set('required', '1')
                        
                    fiscal_operations = eview.xpath("//field[@name='fiscal_operation_id']")
                    for fiscal_operation_id in fiscal_operations:
                        fiscal_operation_id.set('domain', "[('fiscal_type','=','service'),('type','=','input'),('fiscal_operation_category_id','=',fiscal_operation_category_id),('use_invoice','=',True)]")
                        fiscal_operation_id.set('required', '1')
                
                if context['type'] in ('out_invoice', 'in_refund'):  
                    fiscal_operation_categories = eview.xpath("//field[@name='fiscal_operation_category_id']")
                    for fiscal_operation_category_id in fiscal_operation_categories:
                        fiscal_operation_category_id.set('domain', "[('fiscal_type','=','service'),('type','=','output'),('use_invoice','=',True)]")
                        fiscal_operation_category_id.set('required', '1')
                    
                    fiscal_operations = eview.xpath("//field[@name='fiscal_operation_id']")
                    for fiscal_operation_id in fiscal_operations:
                        fiscal_operation_id.set('domain', "[('fiscal_type','=','service'),('type','=','output'),('fiscal_operation_category_id','=',fiscal_operation_category_id),('use_invoice','=',True)]")
                        fiscal_operation_id.set('required', '1')
            
            result['arch'] = etree.tostring(eview)
        
        if view_type == 'tree':
            doc = etree.XML(result['arch'])
            nodes = doc.xpath("//field[@name='partner_id']")
            partner_string = _('Customer')
            if context.get('type', 'out_invoice') in ('in_invoice', 'in_refund'):
                partner_string = _('Supplier')
            for node in nodes:
                node.set('string', partner_string)
            result['arch'] = etree.tostring(doc)
        
        return result
    
    def _amount_tax_icms(self, cr, uid, tax=False):
        result = {
                  'icms_base_type': tax.get('type'),
                  'icms_base': tax.get('total_base', 0.0),
                  'icms_base_other': tax.get('total_base_other', 0.0),
                  'icms_value': tax.get('amount', 0.0),
                  'icms_percent': tax.get('percent', 0.0) * 100,
                  'icms_percent_reduction': tax.get('base_reduction') * 100,
                  }
        return result
    
    def _amount_tax_icmsst(self, cr, uid, tax=False):
        result = {
                  'icms_st_base_type': tax.get('type'),
                  'icms_st_value': tax.get('amount', 0.0),
                  'icms_st_base': tax.get('total_base', 0.0),
                  'icms_st_percent': tax.get('icms_st_percent', 0.0) * 100,
                  'icms_st_percent_reduction': tax.get('icms_st_percent_reduction', 0.0) * 100,
                  'icms_st_mva': tax.get('amount_mva', 0.0) * 100,
                  'icms_st_base_other': tax.get('icms_st_base_other', 0.0),
                  }
        return result
    
    def _amount_tax_ipi(self, cr, uid, tax=False):
        result = {
                  'ipi_type': tax.get('type'),
                  'ipi_base': tax.get('total_base', 0.0),
                  'ipi_value': tax.get('amount', 0.0),
                  'ipi_percent': tax.get('percent', 0.0) * 100,
                  }
        return result
    
    def _amount_tax_cofins(self, cr, uid, tax=False):
        result = {
                  'cofins_base': tax.get('total_base', 0.0),
                  'cofins_base_other': tax.get('total_base_other', 0.0), #FIXME
                  'cofins_value': tax.get('amount', 0.0),
                  'cofins_percent': tax.get('percent', 0.0) * 100,
                  }
        return result
    
    def _amount_tax_cofinsst(self, cr, uid, tax=False):
        result = {
                  'cofins_st_type': 'percent',
                  'cofins_st_base': 0.0,
                  'cofins_st_percent': 0.0,
                  'cofins_st_value': 0.0,
                  }
        return result
    
    def _amount_tax_pis(self, cr, uid, tax=False):
        result = {
                  'pis_base': tax.get('total_base', 0.0),
                  'pis_base_other': tax.get('total_base'),
                  'pis_value': tax.get('amount', 0.0),
                  'pis_percent': tax.get('percent', 0.0) * 100,
                  }
        return result
    
    def _amount_tax_pisst(self, cr, uid, tax=False):
        result = {
                  'pis_st_type': 'percent',
                  'pis_st_base': 0.0,
                  'pis_st_percent': 0.0, 
                  'pis_st_value': 0.0,
                  }
        return result
    
    def _amount_tax_ii(self, cr, uid, tax=False):
        result = {
                  'ii_base': tax.get('total_base', 0.0),
                  'ii_value': tax.get('amount', 0.0),
                  }
        return result
    
    def _amount_tax_issqn(self, cr, uid, taxes=False):
        pass
    
    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = {
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'icms_base_type': 'percent',
                'icms_base': 0.0,
                'icms_base_other': 0.0,
                'icms_value': 0.0,
                'icms_percent': 0.0,
                'icms_percent_reduction': 0.0,
                'icms_st_base_type': 'percent',
                'icms_st_value': 0.0,
                'icms_st_base': 0.0,
                'icms_st_percent': 0.0,
                'icms_st_percent_reduction': 0.0,
                'icms_st_mva': 0.0,
                'icms_st_base_other': 0.0,
                'icms_cst': '40', #Coloca como isento caso não tenha ICMS
                'ipi_type': 'percent',
                'ipi_base': 0.0,
                'ipi_base_other': 0.0,
                'ipi_value': 0.0,
                'ipi_percent': 0.0,
                'ipi_cst': '53', #Coloca como isento caso não tenha IPI
                'pis_type': 'percent',
                'pis_base': 0.0,
                'pis_base_other': 0.0,
                'pis_value': 0.0,
                'pis_percent': 0.0,
                'pis_st_type': 'percent',
                'pis_st_base': 0.0,
                'pis_st_percent': 0.0, 
                'pis_st_value': 0.0,
                'pis_cst': '99', #Coloca como isento caso não tenha PIS]
                'cofins_type': 'percent',
                'cofins_base': 0.0,
                'cofins_base_other': 0.0,
                'cofins_value': 0.0,
                'cofins_percent': 0.0,
                'cofins_st_type': 'percent',
                'cofins_st_base': 0.0,
                'cofins_st_percent': 0.0,
                'cofins_st_value': 0.0,
                'cofins_cst': '99', #Coloca como isento caso não tenha COFINS
                'ii_base': 0.0,
                'ii_value': 0.0,
            }
            price = line.price_unit * (1-(line.discount or 0.0)/100.0)
            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, address_id=line.invoice_id.address_invoice_id, partner=line.invoice_id.partner_id, fiscal_operation=line.fiscal_operation_id)
            
            icms_cst = '99'
            ipi_cst = '99'
            pis_cst = '99'
            cofins_cst = '99'
            company_id = line.company_id.id and line.invoice_id.company_id.id or False
            
            if line.fiscal_operation_id:

                fiscal_operation_ids = self.pool.get('l10n_br_account.fiscal.operation.line').search(cr, uid, [('company_id','=',company_id),('fiscal_operation_id','=',line.fiscal_operation_id.id),('fiscal_classification_id','=',False)], order="fiscal_classification_id")
                for fo_line in self.pool.get('l10n_br_account.fiscal.operation.line').browse(cr, uid, fiscal_operation_ids):
                    if fo_line.tax_code_id.domain == 'icms':
                        icms_cst = fo_line.cst_id.code
                    elif fo_line.tax_code_id.domain == 'ipi':
                        ipi_cst = fo_line.cst_id.code
                    elif fo_line.tax_code_id.domain == 'pis':
                        pis_cst = fo_line.cst_id.code
                    elif fo_line.tax_code_id.domain == 'cofins':
                        cofins_cst = fo_line.cst_id.code

                if line.product_id:
                    fo_ids_ncm = self.pool.get('l10n_br_account.fiscal.operation.line').search(cr, uid, [('company_id','=',company_id),('fiscal_operation_id','=',line.fiscal_operation_id.id),('fiscal_classification_id','=',line.product_id.property_fiscal_classification.id)])
    
                    for fo_line_ncm in self.pool.get('l10n_br_account.fiscal.operation.line').browse(cr, uid, fo_ids_ncm):
                        if fo_line_ncm.tax_code_id.domain == 'icms':
                            icms_cst = fo_line_ncm.cst_id.code
                        elif fo_line_ncm.tax_code_id.domain == 'ipi':
                            ipi_cst = fo_line_ncm.cst_id.code
                        elif fo_line_ncm.tax_code_id.domain == 'pis':
                            pis_cst = fo_line_ncm.cst_id.code
                        elif fo_line_ncm.tax_code_id.domain == 'cofins':
                            cofins_cst = fo_line_ncm.cst_id.code

            for tax in taxes['taxes']:
                try:
                    amount_tax = getattr(self, '_amount_tax_%s' % tax.get('domain', ''))
                    res[line.id].update(amount_tax(cr, uid, tax))
                except AttributeError:
                    # Caso não exista campos especificos dos impostos
                    # no documento fiscal, os mesmos são calculados.
                    continue

            if line.invoice_id:
                currency = line.invoice_id.currency_id
                res[line.id].update({
                                'price_subtotal': cur_obj.round(cr, uid, currency, taxes['total'] - taxes['total_tax_discount']),
                                'price_total': cur_obj.round(cr, uid, currency, taxes['total']),
                                'icms_cst': icms_cst,
                                'ipi_cst': ipi_cst,
                                'pis_cst': pis_cst,
                                'cofins_cst': cofins_cst,
                                })

        return res

    _columns = {
                'fiscal_operation_category_id': fields.many2one('l10n_br_account.fiscal.operation.category', 'Categoria'),
                'fiscal_operation_id': fields.many2one('l10n_br_account.fiscal.operation', 'Operação Fiscal', domain="[('fiscal_operation_category_id','=',fiscal_operation_category_id)]"),
                'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position', domain="[('fiscal_operation_id','=',fiscal_operation_id)]"),
                'cfop_id': fields.many2one('l10n_br_account.cfop', 'CFOP'),
                'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal', type="float",
                                                  digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'price_total': fields.function(_amount_line, method=True, string='Total', type="float",
                                               digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_base_type': fields.function(_amount_line, method=True, string='Tipo Base ICMS', type="char", size=64,
                                              store=True, multi='all'),
                'icms_base': fields.function(_amount_line, method=True, string='Base ICMS', type="float",
                                             digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_base_other': fields.function(_amount_line, method=True, string='Base ICMS Outras', type="float",
                                             digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_value': fields.function(_amount_line, method=True, string='Valor ICMS', type="float",
                                              digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_percent': fields.function(_amount_line, method=True, string='Perc ICMS', type="float",
                                                digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_percent_reduction': fields.function(_amount_line, method=True, string='Perc Redução de Base ICMS', type="float",
                                                digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_st_base_type': fields.function(_amount_line, method=True, string='Tipo Base ICMS ST', type="char", size=64,
                                              store=True, multi='all'),
                'icms_st_value': fields.function(_amount_line, method=True, string='Valor ICMS ST', type="float",
                                              digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_st_base': fields.function(_amount_line, method=True, string='Base ICMS ST', type="float",
                                              digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_st_percent': fields.function(_amount_line, method=True, string='Percentual ICMS ST', type="float",
                                              digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_st_percent_reduction': fields.function(_amount_line, method=True, string='Perc Redução de Base ICMS ST', type="float",
                                                digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_st_mva': fields.function(_amount_line, method=True, string='MVA ICMS ST', type="float",
                                              digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_st_base_other': fields.function(_amount_line, method=True, string='Base ICMS ST Outras', type="float",
                                              digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'icms_cst': fields.function(_amount_line, method=True, string='CST ICMS', type="char", size=3,
                                              store=True, multi='all'),
                'ipi_type': fields.function(_amount_line, method=True, string='Tipo do IPI', type="char", size=64,
                                              store=True, multi='all'),
                'ipi_base': fields.function(_amount_line, method=True, string='Base IPI', type="float",
                                            digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'ipi_base_other': fields.function(_amount_line, method=True, string='Base IPI Outras', type="float",
                                            digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'ipi_value': fields.function(_amount_line, method=True, string='Valor IPI', type="float",
                                                  digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'ipi_percent': fields.function(_amount_line, method=True, string='Perc IPI', type="float",
                                               digits_compute= dp.get_precision('Account'), store=True, multi='all'),
                'ipi_cst': fields.function(_amount_line, method=True, string='CST IPI', type="char", size=2,
                                           store=True, multi='all'),
                'pis_type': fields.function(_amount_line,
                                            method=True,
                                            string='Tipo do PIS',
                                            type="char",
                                            size=64,
                                            store=True,
                                            multi='all'),
                'pis_base': fields.function(_amount_line,
                                            method=True,
                                            string='Base PIS',
                                            type="float",
                                            digits_compute=dp.get_precision('Account'),
                                            store=True,
                                            multi='all'),
                'pis_base_other': fields.function(_amount_line,
                                                  method=True,
                                                  string='Base PIS Outras',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True,
                                                  multi='all'),
                'pis_value': fields.function(_amount_line,
                                             method=True,
                                             string='Valor PIS',
                                             type="float",
                                             digits_compute=dp.get_precision('Account'),
                                             store=True,
                                             multi='all'),
                'pis_percent': fields.function(_amount_line,
                                               method=True,
                                               string='Perc PIS',
                                               type="float",
                                               digits_compute=dp.get_precision('Account'),
                                               store=True,
                                               multi='all'),
                'pis_cst': fields.function(_amount_line,
                                           method=True,
                                           string='CST PIS',
                                           type="char",
                                           size=2,
                                           store=True,
                                           multi='all'),
                'pis_st_type': fields.function(_amount_line,
                                               method=True,
                                               string='Calculo PIS ST',
                                               type="char",
                                               size=64,
                                               store=True,
                                               multi='all'),
                'pis_st_base': fields.function(_amount_line,
                                               method=True,
                                               string='Base PIS ST',
                                               type="float",
                                               digits_compute=dp.get_precision('Account'),
                                               store=True,
                                               multi='all'),
                'pis_st_percent': fields.function(_amount_line,
                                                  method=True,
                                                  string='Perc PIS ST',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True,
                                                  multi='all'),
                'pis_st_value': fields.function(_amount_line,
                                                method=True,
                                                string='Valor PIS ST',
                                                type="float",
                                                digits_compute=dp.get_precision('Account'),
                                                store=True,
                                                multi='all'),
                'cofins_type': fields.function(_amount_line, 
                                               method=True, 
                                               string='Tipo do COFINS', 
                                               type="char", 
                                               size=64,
                                               store=True, 
                                               multi='all'),
                'cofins_base': fields.function(_amount_line,
                                               method=True,
                                               string='Base COFINS',
                                               type="float",
                                               digits_compute=dp.get_precision('Account'),
                                               store=True, multi='all'),
                'cofins_base_other': fields.function(_amount_line,
                                                     method=True,
                                                     string='Base COFINS Outras',
                                                     type="float",
                                                     digits_compute=dp.get_precision('Account'),
                                                     store=True,
                                                     multi='all'),
                'cofins_value': fields.function(_amount_line,
                                                method=True,
                                                string='Valor COFINS',
                                                type="float",
                                                digits_compute=dp.get_precision('Account'),
                                                store=True,
                                                multi='all'),
                'cofins_percent': fields.function(_amount_line,
                                                  method=True,
                                                  string='Perc COFINS',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True, multi='all'),
                'cofins_cst': fields.function(_amount_line,
                                              method=True,
                                              string='Valor COFINS',
                                              type="char",
                                              size=2,
                                              store=True,
                                              multi='all'),
                'cofins_st_type': fields.function(_amount_line,
                                                  method=True,
                                                  string='Calculo COFINS ST',
                                                  type="char",
                                                  size=64,
                                                  store=True,
                                                  multi='all'),
                'cofins_st_base': fields.function(_amount_line,
                                                  method=True,
                                                  string='Base COFINS ST',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True,
                                                  multi='all'),
                'cofins_st_percent': fields.function(_amount_line,
                                                  method=True,
                                                  string='Perc COFINS ST',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True,
                                                  multi='all'),
                'cofins_st_value': fields.function(_amount_line,
                                                  method=True,
                                                  string='Valor COFINS ST',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True,
                                                  multi='all'),
                'ii_base': fields.function(_amount_line,
                                                  method=True,
                                                  string='Base II',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True,
                                                  multi='all'),
                'ii_value': fields.function(_amount_line,
                                                  method=True,
                                                  string='Valor II',
                                                  type="float",
                                                  digits_compute=dp.get_precision('Account'),
                                                  store=True,
                                                  multi='all'),
                'ii_iof': fields.float('Valor IOF', required=True,
                                       digits_compute= dp.get_precision('Account')),
                'ii_customhouse_charges': fields.float('Depesas Atuaneiras', 
                                                       required=True,
                                                       digits_compute=dp.get_precision('Account')),
                }
    _defaults = {
                 'ii_iof': 0.0,
                 'ii_customhouse_charges': 0.0,
                 }

    def _fiscal_position_map(self, cr, uid, ids, partner_id, partner_invoice_id, company_id, fiscal_operation_category_id):
        result = {'fiscal_operation_id': False, 'cfop_id': False}
        obj_rule = self.pool.get('account.fiscal.position.rule')
        fiscal_result = obj_rule.fiscal_position_map(cr, uid, partner_id, partner_invoice_id, company_id, fiscal_operation_category_id, context={'use_domain': ('use_invoice','=',True)})
        result.update(fiscal_result)
        if result.get('fiscal_operation_id', False):
            obj_foperation = self.pool.get('l10n_br_account.fiscal.operation').browse(cr, uid, result['fiscal_operation_id'])
            result['cfop_id'] = obj_foperation.cfop_id.id
        return result

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', 
                          type='out_invoice', partner_id=False, fposition_id=False, 
                          price_unit=False, address_invoice_id=False, currency_id=False, 
                          context=None, company_id=False, fiscal_operation_category_id=False, 
                          fiscal_operation_id=False):
        result = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, 
                                                                     type, partner_id, fposition_id, price_unit, 
                                                                     address_invoice_id, currency_id, context, company_id)
        if not fiscal_operation_category_id or not product:
            return result

        obj_fiscal_position_rule = self.pool.get('account.fiscal.position.rule')
        product_fiscal_category_id = obj_fiscal_position_rule.product_fiscal_category_map(cr, uid, product, fiscal_operation_category_id)

        if not product_fiscal_category_id:
            result['value']['fiscal_operation_category_id'] = fiscal_operation_category_id
            result['value']['fiscal_operation_id'] = fiscal_operation_id
            if fiscal_operation_id:
                result['value']['fiscal_operation_id'] = fiscal_operation_id
                result['value']['cfop_id'] = self.pool.get('l10n_br_account.fiscal.operation').read(cr, uid, [fiscal_operation_id], ['cfop_id'])[0]['cfop_id']
            return result

        result['value']['fiscal_operation_category_id'] = product_fiscal_category_id
        result['value']['fiscal_operation_id'] = False

        fiscal_data = self._fiscal_position_map(cr, uid, ids, partner_id, address_invoice_id, company_id, product_fiscal_category_id)
        result['value'].update(fiscal_data)
        return result

account_invoice_line()


class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"
    _description = "Invoice Tax"

    def compute(self, cr, uid, invoice_id, context={}):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context)
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id.id

        for line in inv.invoice_line:
            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id, fiscal_operation=line.fiscal_operation_id)
            for tax in taxes['taxes']:
                val = {}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = tax['total_base']
                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']
        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped
    
account_invoice_tax()