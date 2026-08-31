# -*- coding: utf-8 -*-
import logging
import json
import requests

from odoo import _, models
from odoo.exceptions import UserError
from datetime import date

_logger = logging.getLogger(__name__)

PLANNERPRO_TIMEOUT = 15  # segundos, evita que la UI se quede colgada
# Nombres de los parámetros de configuración (System Parameters).
# Se leen/escriben también desde res.config.settings (ver res_config_settings.py)
PARAM_ENDPOINT_URL = "stock_plannerpro_connector.endpoint_url"
PARAM_API_KEY = "stock_plannerpro_connector.api_key"


class StockPicking(models.Model):
    """Herencia de stock.picking (patrón _inherit, NO se toca el core).

    Este modelo solo se encarga de:
      1) Validar la selección hecha por el usuario en la vista lista.
      2) Identificar las cotizaciones (sale.order) únicas ligadas a esa
         selección.
      3) Delegar a sale.order la construcción de "su" payload.
      4) Hacer la llamada HTTP a PlannerPro con el payload consolidado.

    Referencia: ORM API / Inheritance and extension
    https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html
    """
    _inherit = "stock.picking"

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------
    def _plannerpro_get_config(self):
        """Obtiene URL y API Key desde los Parámetros del Sistema.

        Nunca hardcodeamos credenciales en el código: se guardan en
        ir.config_parameter (Ajustes > Técnico > Parámetros del sistema),
        configurables también desde Ajustes > pestaña PlannerPro.
        """
        icp = self.env["ir.config_parameter"].sudo()
        url = icp.get_param(PARAM_ENDPOINT_URL)
        api_key = icp.get_param(PARAM_API_KEY)
        if not url or not api_key:
            raise UserError(_(
                "PlannerPro no está configurado todavía.\n"
                "Ve a Ajustes > pestaña PlannerPro y completa la URL del "
                "endpoint y la API Key."
            ))
        return url, api_key

    # ------------------------------------------------------------------
    # Acción principal (llamada desde el menú de Acciones ⚙️)
    # ------------------------------------------------------------------
    def action_send_to_plannerpro(self):
        """Envía a PlannerPro las cotizaciones ligadas a las Órdenes de
        Entrega seleccionadas (self = recordset multi-registro).

        Se registra como ir.actions.server con binding_model_id y
        binding_view_types='list' (ver data/server_action_data.xml),
        por lo que 'self' contiene TODOS los stock.picking marcados en
        la vista lista al momento de hacer clic en la acción.

        Diseño: si dos entregas seleccionadas pertenecen a la MISMA
        cotización, esta se envía UNA sola vez (deduplicada), con la
        lista de nombres de las entregas que la originaron en el campo
        'related_deliveries' del payload, para trazabilidad.
        """
        if not self:
            raise UserError(_("Selecciona al menos una Orden de Entrega."))

        # Regla de negocio: solo operaciones de tipo Salida (entrega)
        non_delivery = self.filtered(
            lambda p: p.picking_type_id.code != "outgoing"
        )
        if non_delivery:
            raise UserError(_(
                "'Enviar a PlannerPro' solo admite Órdenes de Entrega "
                "(operaciones de salida). Excluye de tu selección: %s"
            ) % ", ".join(non_delivery.mapped("name")))

        # Regla de negocio: toda entrega seleccionada debe tener una
        # cotización/orden de venta ligada (campo sale_id, añadido por
        # el módulo sale_stock).
        without_sale_order = self.filtered(lambda p: not p.sale_id)
        if without_sale_order:
            raise UserError(_(
                "Las siguientes Órdenes de Entrega no tienen una "
                "cotización/orden de venta asociada, por lo que no se "
                "puede armar la información para PlannerPro: %s"
            ) % ", ".join(without_sale_order.mapped("name")))

        url, api_key = self._plannerpro_get_config()

        # Agrupar las entregas seleccionadas por cotización única,
        # conservando de qué entrega(s) viene cada una (trazabilidad).
        picking_names_by_order = {}
        for picking in self:
            order = picking.sale_id
            picking_names_by_order.setdefault(order, []).append(picking.name)

        payload = {
            "name": f"Ruta del {date.today().isoformat()}",
            "stops":[
                order._plannerpro_prepare_quotation_payload(
                    picking_names=names
                )
                for order, names in picking_names_by_order.items()
            ]
        }

        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            # Nombre de header de ejemplo; ajústalo al que exija la
            # documentación real de la API de PlannerPro (p. ej.
            # 'Authorization: Bearer <token>' o 'X-API-KEY').
            #"Authorization": api_key,
        }

        try:
            body = json.dumps(payload, default=str, ensure_ascii=False)
            response = requests.post(
                url,
                data=body.encode("utf-8"),
            #response = requests.post(
                #url,
                #json=payload,
                headers=headers,
                timeout=PLANNERPRO_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            _logger.error(
                "Fallo al llamar a la API de PlannerPro: %s", exc
            )
            raise UserError(_(
                "No se pudo enviar la información a PlannerPro.\n"
                "Detalle técnico: %s"
            ) % exc) from exc

        # Traza de auditoría en el chatter de cada picking.
        # stock.picking incluye mail.thread de forma nativa (chatter).
        for picking in self:
            picking.message_post(
                body=_("Enviado a PlannerPro correctamente (cotización %s).")
                % picking.sale_id.name
            )

        # Notificación flotante estándar de Odoo (ir.actions.client /
        # display_notification).
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("PlannerPro"),
                "message": _(
                    "%s cotización(es) enviada(s) correctamente a "
                    "PlannerPro, a partir de %s Orden(es) de Entrega."
                ) % (len(picking_names_by_order), len(self)),
                "type": "success",
                "sticky": False,
            },
        }
