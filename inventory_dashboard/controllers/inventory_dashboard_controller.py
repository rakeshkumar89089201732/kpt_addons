# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import http
from odoo.http import request
from collections import defaultdict


class InventoryDashboardController(http.Controller):

    @http.route('/inventory_dashboard', type='http', auth='user', website=False)
    def inventory_dashboard(self):
        """Render inventory dashboard page"""
        return request.render('inventory_dashboard.inventory_dashboard_template', {})

    @http.route('/inventory_dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        """Get dashboard data via JSON"""
        from datetime import datetime, timedelta
        
        # Get low stock products
        low_stock_products = request.env['product.product'].search([
            ('type', '=', 'product'),
            ('qty_available', '>', 0),
        ]).filtered(lambda p: p.qty_available <= p.reordering_min_qty if p.reordering_min_qty > 0 else False)
        
        # Get recent stock moves
        recent_moves = request.env['stock.move'].search([
            ('state', '=', 'done'),
        ], limit=10, order='date desc')
        
        # Get top products by quantity
        top_products = request.env['product.product'].search([
            ('type', '=', 'product'),
            ('qty_available', '>', 0),
        ], limit=10, order='qty_available desc')
        
        # Get warehouse summary
        warehouses = request.env['stock.warehouse'].search([])
        warehouse_data = []
        for warehouse in warehouses:
            quants = request.env['stock.quant'].search([
                ('location_id', 'child_of', warehouse.lot_stock_id.id),
            ])
            total_qty = sum(quants.mapped('quantity'))
            total_value = sum(quants.mapped('inventory_value'))
            warehouse_data.append({
                'id': warehouse.id,
                'name': warehouse.name,
                'total_qty': total_qty,
                'total_value': total_value,
            })
        
        # Get stock valuation
        quants = request.env['stock.quant'].search([
            ('quantity', '>', 0),
        ])
        total_stock_value = sum(quants.mapped('inventory_value'))
        total_products = request.env['product.product'].search_count([
            ('type', '=', 'product'),
        ])
        total_locations = request.env['stock.location'].search_count([
            ('usage', '=', 'internal'),
        ])
        
        # Get category summary
        categories = request.env['product.category'].search([])
        category_data = []
        category_value_data = []
        for category in categories[:10]:
            products = request.env['product.product'].search([
                ('categ_id', '=', category.id),
                ('type', '=', 'product'),
            ])
            total_qty = sum(products.mapped('qty_available'))
            category_quants = request.env['stock.quant'].search([
                ('product_id', 'in', products.ids),
                ('quantity', '>', 0),
            ])
            category_value = sum(category_quants.mapped('inventory_value'))
            category_data.append({
                'id': category.id,
                'name': category.name,
                'total_qty': total_qty,
                'product_count': len(products),
            })
            category_value_data.append({
                'id': category.id,
                'name': category.name,
                'value': category_value,
            })
        
        # Calculate Inventory Turnover (simplified: COGS / Average Inventory)
        # For now, using a simplified calculation based on recent moves
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)
        recent_outbound = request.env['stock.move'].search([
            ('state', '=', 'done'),
            ('date', '>=', thirty_days_ago.strftime('%Y-%m-%d')),
            ('location_dest_id.usage', '=', 'customer'),
        ])
        cogs = sum(recent_outbound.mapped('value'))
        avg_inventory = total_stock_value if total_stock_value > 0 else 1
        inventory_turnover = (cogs / avg_inventory) * 12 if avg_inventory > 0 else 0  # Annualized
        
        # Stock Aging 90+ Days
        ninety_days_ago = today - timedelta(days=90)
        aging_quants = request.env['stock.quant'].search([
            ('quantity', '>', 0),
            ('in_date', '<', ninety_days_ago.strftime('%Y-%m-%d')),
        ])
        aging_value = sum(aging_quants.mapped('inventory_value'))
        aging_count = len(aging_quants.mapped('product_id'))
        
        # Top 10 Moving Products (by quantity moved in last 30 days)
        moving_products = defaultdict(float)
        recent_moves_all = request.env['stock.move'].search([
            ('state', '=', 'done'),
            ('date', '>=', thirty_days_ago.strftime('%Y-%m-%d')),
        ])
        for move in recent_moves_all:
            if move.product_id.type == 'product':
                moving_products[move.product_id.id] += abs(move.quantity_done)
        
        top_moving = sorted(moving_products.items(), key=lambda x: x[1], reverse=True)[:10]
        top_moving_products = []
        for product_id, qty in top_moving:
            product = request.env['product.product'].browse(product_id)
            top_moving_products.append({
                'id': product.id,
                'name': product.name,
                'quantity_moved': qty,
            })
        
        # Inbound vs Outbound (Monthly Graph - Last 6 months)
        monthly_data = []
        for i in range(5, -1, -1):
            month_start = (today - timedelta(days=30*i)).replace(day=1)
            if i == 0:
                month_end = today
            else:
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1) - timedelta(days=1)
            
            inbound = request.env['stock.move'].search([
                ('state', '=', 'done'),
                ('date', '>=', month_start.strftime('%Y-%m-%d')),
                ('date', '<=', month_end.strftime('%Y-%m-%d')),
                ('location_id.usage', '!=', 'internal'),
                ('location_dest_id.usage', '=', 'internal'),
            ])
            outbound = request.env['stock.move'].search([
                ('state', '=', 'done'),
                ('date', '>=', month_start.strftime('%Y-%m-%d')),
                ('date', '<=', month_end.strftime('%Y-%m-%d')),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '!=', 'internal'),
            ])
            
            inbound_qty = sum(inbound.mapped('quantity_done'))
            outbound_qty = sum(outbound.mapped('quantity_done'))
            
            monthly_data.append({
                'month': month_start.strftime('%b %Y'),
                'inbound': inbound_qty,
                'outbound': outbound_qty,
            })
        
        # Slow Moving Items (products with no movement in last 90 days)
        slow_moving_products = []
        products_with_moves = set(recent_moves_all.mapped('product_id').ids)
        all_products = request.env['product.product'].search([
            ('type', '=', 'product'),
            ('qty_available', '>', 0),
        ])
        for product in all_products:
            if product.id not in products_with_moves:
                product_quants = request.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('quantity', '>', 0),
                ])
                slow_moving_products.append({
                    'id': product.id,
                    'name': product.name,
                    'qty_available': product.qty_available,
                    'value': sum(product_quants.mapped('inventory_value')),
                })
        slow_moving_products = sorted(slow_moving_products, key=lambda x: x['value'], reverse=True)[:10]
        
        return {
            'low_stock_products': [{
                'id': p.id,
                'name': p.name,
                'qty_available': p.qty_available,
                'reordering_min_qty': p.reordering_min_qty,
            } for p in low_stock_products[:10]],
            'recent_moves': [{
                'id': m.id,
                'product': m.product_id.name,
                'quantity': m.quantity_done,
                'date': m.date.strftime('%Y-%m-%d %H:%M') if m.date else '',
                'reference': m.reference or '',
                'location_from': m.location_id.name,
                'location_to': m.location_dest_id.name,
            } for m in recent_moves],
            'top_products': [{
                'id': p.id,
                'name': p.name,
                'qty_available': p.qty_available,
                'standard_price': p.standard_price,
            } for p in top_products],
            'warehouses': warehouse_data,
            'total_stock_value': total_stock_value,
            'total_products': total_products,
            'total_locations': total_locations,
            'categories': category_data,
            # Executive View Metrics
            'inventory_turnover': round(inventory_turnover, 2),
            'stock_aging_90_days_value': aging_value,
            'stock_aging_90_days_count': aging_count,
            'low_stock_count': len(low_stock_products),
            'top_moving_products': top_moving_products,
            # Analytical View Data
            'monthly_inbound_outbound': monthly_data,
            'category_stock_value': sorted(category_value_data, key=lambda x: x['value'], reverse=True)[:10],
            'slow_moving_items': slow_moving_products,
        }
