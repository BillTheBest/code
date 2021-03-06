# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
# Copyright (C) 2009  Renato Lima - Akretion                                    #
#                                                                               #
#This program is free software: you can redistribute it and/or modify           #
#it under the terms of the GNU General Public License as published by           #
#the Free Software Foundation, either version 3 of the License, or              #
#(at your option) any later version.                                            #
#                                                                               #
#This program is distributed in the hope that it will be useful,                #
#but WITHOUT ANY WARRANTY; without even the implied warranty of                 #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                  #
#GNU General Public License for more details.                                   #
#                                                                               #
#You should have received a copy of the GNU General Public License              #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.          #
#################################################################################

from osv import osv, fields

class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _description = "Picking List"

    _columns = {
                'fiscal_operation_category_id': fields.many2one('l10n_br.fiscal.operation.category', 'Categoria'),
                'fiscal_operation_id': fields.many2one('l10n_br.fiscal.operation', 'Operação Fiscal', domain="[('fiscal_operation_category_id','=',fiscal_operation_category_id)]"),
                'fiscal_position': fields.many2one('account.fiscal.position', 'Posição Fiscal', domain="[('fiscal_operation_id','=',fiscal_operation_id)]"),
                }
    
    #TODO Fazer a dedução da operação e posição fiscal ao mudar o parceiro
    def onchange_partner_in(self, cr, uid, context=None, partner_id=None,fiscal_operation_category_id=False,company_id=False):

        result = super(stock_picking, self).onchange_partner_in(cr, uid, context, partner_id)
        
        result = {'value':{}}
        
        if not fiscal_operation_category_id or not company_id or not partner_id:
            return result
        
        partner_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [partner_id])[0]
        
        to_country = partner_addr_default.country_id.id
        to_state = partner_addr_default.state_id.id
        
        obj_partner = self.pool.get('res.partner').browse(cr, uid, [partner_addr_default.partner_id.id])[0]
        fiscal_position = obj_partner.property_account_position
        partner_fiscal_type = obj_partner.partner_fiscal_type_id.id

        if fiscal_position:
            result['value']['fiscal_position'] = fiscal_position
            result['value']['fiscal_operation_id'] = obj_partner.property_account_position.fiscal_operation_id.id
            return result

        obj_company = self.pool.get('res.company').browse(cr, uid, [company_id])[0]

        company_addr = self.pool.get('res.partner').address_get(cr, uid, [obj_company.partner_id.id], ['default'])
        company_addr_default = self.pool.get('res.partner.address').browse(cr, uid, [company_addr['default']])[0]
        
        from_country = company_addr_default.country_id.id
        from_state = company_addr_default.state_id.id
        
        fsc_pos_id = self.pool.get('account.fiscal.position.rule').search(cr, uid, [('company_id','=', company_id),('from_country','=',from_country),('from_state','=',from_state),('to_country','=',to_country),('to_state','=',to_state),('use_sale','=',True),('fiscal_operation_category_id','=',fiscal_operation_category_id),('partner_fiscal_type_id','=',partner_fiscal_type),('use_picking','=',True)])
        if fsc_pos_id:
            obj_fpo_rule = self.pool.get('account.fiscal.position.rule').browse(cr, uid, fsc_pos_id)[0]
            result['value']['fiscal_position'] = obj_fpo_rule.fiscal_position_id.id
            result['value']['fiscal_operation_id'] = obj_fpo_rule.fiscal_position_id.fiscal_operation_id.id

        return result

    def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
        '''Call after the creation of the invoice line'''

        self.pool.get('account.invoice.line').write(cr, uid, invoice_line_id, {'cfop_id': move_line.picking_id.fiscal_operation_id.cfop_id.id})

        return super(stock_picking, self)._invoice_line_hook(cr, uid, move_line, invoice_line_id)

    def _invoice_hook(self, cr, uid, picking, invoice_id):
        '''Call after the creation of the invoice'''

        self.pool.get('account.invoice').write(cr, uid, invoice_id, {'fiscal_operation_category_id': picking.fiscal_operation_category_id.id, 'fiscal_operation_id': picking.fiscal_operation_id.id, 'cfop_id': picking.fiscal_operation_id.cfop_id.id, 'fiscal_document_id': picking.fiscal_operation_id.fiscal_document_id.id, 'fiscal_position': picking.fiscal_position.id})

        return super(stock_picking, self)._invoice_hook(cr, uid, picking, invoice_id)

stock_picking()