# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Extiende los Ajustes (Settings) para exponer la configuración de
    PlannerPro de forma amigable, en vez de obligar al usuario a ir a
    Ajustes > Técnico > Parámetros del Sistema.

    El atributo `config_parameter` en un fields.Char hace que el ORM
    lea/escriba automáticamente en ir.config_parameter, usando la clave
    (key) indicada. Este es un patrón estándar usado en muchos módulos
    core de Odoo para ajustes globales tipo API key/URL.
    """
    _inherit = "res.config.settings"

    stock_plannerpro_endpoint_url = fields.Char(
        string="URL del endpoint de PlannerPro",
        config_parameter="stock_plannerpro_connector.endpoint_url",
        help="Ej: https://api.plannerpro.com/v1/deliveries",
    )
    stock_plannerpro_api_key = fields.Char(
        string="API Key de PlannerPro",
        config_parameter="stock_plannerpro_connector.api_key",
    )
