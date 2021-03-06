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

{
    'name': 'l10n_br Produto',
    'version': '0.1',
    'category': 'Generic Modules',
    'license': 'AGPL-3',
    'description': """
    Modulo de Produtos
    """,
    'author': 'Akretion, OpenERP Brasil',
    'website': 'http://www.openerpbrasil.org',
    'depends': ['l10n_br_account'],
    'init_xml': ['l10n_br_product_data.xml'],
    'update_xml': ['product_view.xml'],
    'test': [],
    'demo_xml': [
                'l10n_br_product_demo.xml',
                 ],
    'installable': True,
    'active': False,
    'auto_install': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
