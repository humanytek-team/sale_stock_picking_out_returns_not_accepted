# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017 Humanytek (<www.humanytek.com>).
#    Manuel Márquez <manuel@humanytek.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp import api, models


class StockPicking(models.Model):
    _inherit='stock.picking'

    @api.model
    def create(self, vals):

        create_result = super(StockPicking, self).create(vals)
        picking_type_delivery_order = self.env.ref('stock.picking_type_out')

        if picking_type_delivery_order:
            if vals.get('origin') and \
                    vals.get('picking_type_id') == \
                    picking_type_delivery_order.id:

                SaleOrder = self.env['sale.order']
                generated_from_sale_order = SaleOrder.search([
                    ('name', '=', vals.get('origin'))])

                if generated_from_sale_order:

                    pick = create_result
                    StockLocation = self.env['stock.location']
                    return_not_accepted_locations_ids = StockLocation.search([
                        ('id', 'child_of', pick.location_id.location_id.id),
                        ('return_not_accepted_location', '=', True)
                        ]).mapped('id')

                    StockQuant = self.env['stock.quant']
                    for location_id in return_not_accepted_locations_ids:

                        location_quants = StockQuant.search([
                            ('location_id', '=', location_id),
                        ])
                        location_partner_quants = location_quants
                        for quant in location_quants:
                            location_moves = quant.history_ids.filtered(
                                lambda sm: sm.location_dest_id.id ==
                                location_id and not sm.origin_returned_move_id)
                            last_move = location_moves.sorted(
                                key=lambda sm: sm.id)[-1]

                            if last_move.partner_id.id != pick.partner_id.id:
                                location_partner_quants -= quant

                        if location_partner_quants:
                            new_picking = create_result.copy({
                                'location_id': location_id,
                                'move_lines': [],
                                'picking_type_id': pick.picking_type_id.id,
                                'state': 'draft',
                                'origin': pick.name,
                                'location_dest_id': pick.location_dest_id.id,
                                })

                            quants_by_product = list()
                            for quant in location_partner_quants:
                                product_added = [item for item in
                                    quants_by_product if
                                    str(quant.product_id.id) in item]
                                if not bool(product_added):
                                    quants_by_product.append({
                                        str(quant.product_id.id): quant.qty,
                                        })
                                else:
                                    product_quants = (item for item in
                                        quants_by_product if
                                        str(quant.product_id.id) in item).next()

                                    product_quants[str(quant.product_id.id)] += \
                                        quant.qty

                            StockMove = self.env['stock.move']

                            for product_quants in quants_by_product:

                                product_id = int(product_quants.keys()[0])
                                Product = self.env['product.product']
                                product = Product.browse(product_id)
                                product_quants_qty = product_quants.values()[0]
                                product_attrs_values = \
                                    product.attribute_value_ids.mapped('name')
                                product_attrs_values = ', '.join(
                                    product_attrs_values
                                )
                                stock_move_name = '{0} ({1})'.format(
                                    product.name, product_attrs_values)

                                StockMove.create({
                                    'name': stock_move_name,
                                    'picking_id': new_picking.id,
                                    'product_id': product_id,
                                    'product_uom': product.uom_id.id,
                                    'product_uom_qty': product_quants_qty,
                                    'state': 'draft',
                                    'location_id': location_id,
                                    'location_dest_id': \
                                        pick.location_dest_id.id,
                                    'picking_type_id': pick.picking_type_id.id,
                                    'warehouse_id': \
                                        pick.picking_type_id.warehouse_id.id,
                                    'procure_method': 'make_to_stock',
                                    'priority': '1',
                                    'company_id': new_picking.company_id.id,
                                    'origin': new_picking.origin,
                                    'group_id': new_picking.group_id.id,
                                    'partner_id': new_picking.partner_id.id,
                                })

                            new_picking.action_confirm()
                            new_picking.action_assign()
        return create_result
