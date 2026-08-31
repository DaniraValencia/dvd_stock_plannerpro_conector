# -*- coding: utf-8 -*-
{
    "name": "Stock PlannerPro Connector",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Envía Órdenes de Entrega seleccionadas a la API externa PlannerPro",
    "description": """
Stock PlannerPro Connector
===========================
Agrega la acción "Enviar a PlannerPro" al menú de Acciones (⚙️) de la
vista lista de Órdenes de Entrega (Inventario > Operaciones > Entregas).

Al ejecutarse sobre una o varias Órdenes de Entrega seleccionadas:
    * Valida que todas las operaciones sean de tipo "Salida" (entrega).
    * Identifica la(s) cotización(es) / orden(es) de venta ligada(s) a
      las entregas seleccionadas.
    * Por cada cotización, arma un payload JSON con: datos del cliente
      (nombre, identificación fiscal, teléfono, correo), dirección de
      entrega, y el detalle de productos (código, descripción, cantidad)
      tomado de las líneas de la cotización.
    * Llama a la API externa de PlannerPro vía HTTP POST, enviando la
      API Key en un header HTTP.

Configuración: Ajustes > pestaña "PlannerPro".
""",
    "author": "Danira Valencia Diaz",
    "depends": ["stock", "sale_stock"],
    "data": [
        "views/res_config_settings_views.xml",
        "data/server_action_data.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
