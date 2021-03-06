# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
# Copyright (C) 2009  Renato Lima - Akretion                                    #
# Copyright (C) 2011  Vinicius Dittgen - PROGE, Leonardo Santagada - PROGE      #
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

{
    'name' : 'Brazilian Localization',
    'description' : 'Brazilian Localization',
    'category' : 'Localisation',
    'license': 'AGPL-3',
    'author': 'Akretion, OpenERP Brasil',
    'website' : 'http://openerpbrasil.org',
    'version' : '0.6',
    'depends': [
        'l10n_br',
        'l10n_br_base',
        'product',
        'account_fiscal_position_rule',
        'account_product_fiscal_classification'
        ],
    'init_xml': [
                 ],
    'update_xml' : [
        'account_view.xml',
        'account.account.template.csv',
        'account.tax.code.template.csv',
        'l10n_br_account_data.xml',
        'l10n_br_account_sequence.xml',
        'account_fiscal_position_rule_view.xml',
        'account_invoice_view.xml',
        'account_invoice_workflow.xml',
        'l10n_br_account_view.xml',
        'partner_view.xml',
        'product_view.xml',
        'res_company_view.xml',
        'security/ir.model.access.csv',
        'security/l10n_br_account_security.xml',
        'wizard/l10n_br_account_nfe_export_view.xml',
        'wizard/nfe_export_from_invoice_view.xml',
                    ],
    'demo_xml': [
        'demo/base_demo.xml',
        'demo/account.account.csv',
        'demo/account.tax.code.csv',
  	    'l10n_br_account_demo.xml',
        'demo/product_demo.xml',
        'demo/account_financial_demo.xml',
        'demo/account_fiscal_demo.xml',
                 ],
    'installable': True,
    'auto_install': True,
}

