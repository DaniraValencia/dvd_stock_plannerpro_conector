# -*- coding: utf-8 -*-
from odoo import models
from datetime import date


class SaleOrder(models.Model):
    """Herencia de sale.order (patrón _inherit).

    Toda la responsabilidad de "cómo se ve una cotización para
    PlannerPro" vive aquí, separada de stock.picking, que solo se
    encarga de identificar QUÉ cotizaciones hay que enviar.

    Referencia: ORM API - Inheritance and extension
    https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html
    """
    _inherit = "sale.order"

    # ------------------------------------------------------------------
    # Cliente
    # ------------------------------------------------------------------
    def _plannerpro_prepare_customer(self):
        """Datos del cliente de la cotización (campo partner_id).

        - nombre           -> partner.name
        - identificación   -> partner.vat  (campo "Tax ID" / "Identification
                               Number" según el campo estándar documentado
                               en Contacts > Additional fields)
        - teléfono         -> partner.phone
        - correo           -> partner.email
        """
        self.ensure_one()
        partner = self.partner_id
        return {
            #"partner_id": partner.id,
            "name": partner.name or "",
            #"identification": partner.vat or "",
            "identification": partner.ref or "x",
            "phone": partner.phone or "",
            "email": partner.email or "",
        }

    # ------------------------------------------------------------------
    # Dirección de entrega
    # ------------------------------------------------------------------
    def _plannerpro_prepare_delivery_address(self):
        """Dirección de entrega de la cotización.

        Se toma de partner_shipping_id (campo "Dirección de Entrega" en
        el formulario de la cotización/orden de venta), que es distinto
        del cliente facturable (partner_invoice_id) o del contacto
        principal (partner_id).
        """
        self.ensure_one()
        shipping = self.partner_shipping_id
        #return shipping.street or "" + "," + shipping.l10n_mx_edi_colony or "" + "," + shipping.zip or "" + "," + shipping.city or "" + "," + shipping.country_id.name or ""
        #return f"{shipping.street} {shipping.street_number} {shipping.street_number2}, {shipping.zip}, {shipping.city}, {shipping.country_id.name}" 
        return f"{shipping.street}, {shipping.street2}, {shipping.zip}, Querétaro, México" 
        #return f"{shipping.street}, {shipping.street2}, {shipping.zip}, {shipping.city}, {shipping.country_id.name}" 
    #{
        #    "partner_id": shipping.id,
        #    "name": shipping.name or "",
        #    "street": shipping.street or "",
        #    "street2": shipping.street2 or "",
        #    "city": shipping.city or "",
        #    "zip": shipping.zip or "",
        #    "state": shipping.state_id.name or "",
        #    "country": shipping.country_id.name or "",
        #}

    # ------------------------------------------------------------------
    # Líneas de producto
    # ------------------------------------------------------------------
    def _plannerpro_prepare_order_lines(self):
        """Detalle de productos de la cotización (sale.order.line).

        Se excluyen las líneas de tipo "sección" o "nota" (display_type
        distinto de False), ya que no representan un producto real.

        NOTA (verificar en tu instancia): no tengo certeza absoluta de
        que 'display_type' se llame exactamente igual en tu build 18.0;
        es un campo estable desde hace varias versiones, pero confírmalo
        en modo desarrollador si tu vista de cotizaciones tiene
        secciones/notas y ves líneas inesperadas en el payload.
        """
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type)
        return [
            {
                #"product_id": line.product_id.id,
                "code": line.product_id.default_code or "",
                "description": line.name or "",
                "quantity": line.product_uom_qty,
                "capacities": [1],
            }
            for line in lines
        ]

    # ------------------------------------------------------------------
    # Payload completo de UNA cotización
    # ------------------------------------------------------------------
    def _plannerpro_prepare_quotation_payload(self, picking_names=None):
        """Arma el dict JSON-serializable de una cotización completa.

        :param picking_names: lista opcional de nombres de Órdenes de
            Entrega (stock.picking) que dispararon el envío de esta
            cotización, solo para trazabilidad en el payload.
        """
        self.ensure_one()
        return {
            "identifier": self.name,
            #"quotation_id": self.id,
            #"related_deliveries": picking_names or [],
            "address": self._plannerpro_prepare_delivery_address(),
            "min_dispatch_date": date.today(),
            "max_dispatch_date": date.today(),
            "window_one_start":"12:00:00",
            "window_one_end":"18:30:00",
            "window_two_start":"",
            "window_two_end":"",
            "service_time":10,
            "priority":1,
            "dispatch_center":"LORSA CDMX",
            "items": self._plannerpro_prepare_order_lines(),        
            "contact": self._plannerpro_prepare_customer(),
        }
