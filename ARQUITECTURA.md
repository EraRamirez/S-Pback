# Arquitectura — S-Pback

> Documento vivo. Se actualiza conforme avanza el desarrollo del proyecto.

## 0. Estado actual vs. arquitectura objetivo

**Importante:** este documento describe la arquitectura objetivo del producto completo (incluyendo el agente por voz). La implementación actual del repo ya sigue el stack objetivo: **Python 3.12 + FastAPI + MongoDB (Motor)**, con JWT + PIN para autenticacion.

**Nota clave del negocio:** en la primera entrega **NO se implementa el registro por voz**. Todo lo referente a Speech-to-Text, agente LangChain y memoria Redis (secciones 7 y 8) queda pospuesto hasta que el CRUD base esté validado.

**Estado de implementación (actualizado 2026-08-27):**

- ✅ Backend migrado de Node/Hono/Drizzle/PostgreSQL a FastAPI/MongoDB.
- ✅ Auth (telefono + PIN, JWT), CRUD de productos, movimientos (venta/compra/ajuste) y `/summary` implementados y con tests (`tests/`, corren contra Mongo simulado con `mongomock-motor`, sin infraestructura real).
- ✅ La lógica de negocio vive en `app/services/movements.py` con la misma forma de entrada/salida que los "tool contracts" de la sección 7.8, para que envolverla como tools de LangChain (fase de voz) no requiera reescribirla.
- ⚠️ Diferencia respecto al modelo de datos original (sección 6.3): el PIN se guarda como `pin_hash` directamente en el documento `Business` (no existe una colección `users` separada), porque en el alcance actual un negocio tiene un solo dueño.
- ✅ El modelo se generalizó para servir a cualquier giro (no solo abarrotes) — ver sección 6.10: productos por pieza o a granel (kg/g), inventario independiente de materia prima, y reporte quincenal con desglose diario de ingresos/egresos. Detalle en secciones 6.10 a 6.12.
- ⏳ Pendiente: Redis, agente LangChain, Speech-to-Text, y el flujo completo de voz — todo en secciones 7 y 8, sin implementar.

---

## 1. Objetivo de la arquitectura

Definir la estructura técnica del sistema que soportará el MVP del Agente de Inventario por Voz para abarrotes de colonia en CDMX.

**Nota de generalización:** el modelo de datos se generalizó (sección 6.10-6.12) para que el mismo sistema sirva también a otros giros pequeños con lógica similar pero venta a granel además de por pieza (ej. un molino de masa para tamal), sin cambiar el nicho de mercado principal ni la propuesta de valor definida en Fundamentos — es una decisión técnica para no tener que rediseñar el esquema si el producto se ofrece a un giro distinto.

La arquitectura está diseñada para:

- Validar el producto en el mercado
- Permitir iteración rápida
- Priorizar simplicidad operativa
- Ofrecer experiencia natural por voz (fase posterior)
- Mantener posibilidad de escalar en el futuro

Esta arquitectura no busca la perfección enterprise. Busca validación real del problema y disposición de pago.

## 2. Principios estratégicos (alineados al nicho)

Nicho: dueños de abarrotes 45–70 años que usan celular, no quieren sistemas complejos, y llevan inventario en libreta o de memoria.

1. Mobile-first
2. Experiencia simple
3. Interacción natural por voz (fase posterior)
4. Sin complejidad contable
5. Sin integraciones externas
6. Iteración rápida sobre infraestructura compleja

## 3. Componentes del sistema (objetivo)

1. Frontend Web (Mobile First) — repo [SAAS-PYMES](https://github.com/EraRamirez/SAAS-PYMES)
2. Servicio Speech-to-Text (fase posterior)
3. Backend persistente (FastAPI)
4. Agente inteligente (LangChain) (fase posterior)
5. Redis (memoria conversacional) (fase posterior)
6. MongoDB (base de datos principal)

## 4. Arquitectura de alto nivel (objetivo, con voz)

```
Usuario (Dueño del Abarrote)
       │
       ▼
Web App (Mobile First)
       │
       ▼
Speech-to-Text
       │
       ▼
Backend FastAPI
       │
       ├── Agente LangChain
       │       ├── Memoria (Redis)
       │       ├── Context Loader (MongoDB)
       │       └── Tool Router
       │
       ▼
Tools (lógica de negocio)
       │
       ▼
MongoDB
```

Para la primera entrega (sin voz), el flujo se reduce a: Web App → Backend → lógica de negocio → MongoDB, sin STT, agente, ni Redis.

## 5. Backend — FastAPI persistente

### Decisión estratégica

Se utiliza un backend persistente (FastAPI + Docker) en lugar de serverless (Lambdas), porque:

- El agente requiere mantener estado
- Se necesita conexión estable a Redis
- Se requiere mejor experiencia de latencia
- Se necesita facilidad de debugging
- Se prioriza iteración rápida en Sprint 0

### Responsabilidades

- Recibir comandos desde frontend
- Enviar texto al agente (fase posterior)
- Ejecutar tools seleccionadas
- Gestionar autenticación básica
- Orquestar Redis y MongoDB (fase posterior)

## 6. Modelo de datos (MVP)

### 6.1 Objetivo del modelo

Soporta gestión de productos, registro de ventas/compras (manual primero, por voz después), control automático de stock, cálculo automático de ganancia estimada, alertas simples de inventario bajo, y auditoría básica de movimientos. Diseñado para una sola sucursal, un solo dueño, simplicidad operativa e iteración rápida.

### 6.2 Arquitectura del dominio

```
Business (1)
  │
  ├── Product (N)
  │       │
  │       └── InventoryMovement (N)
  │
  └── InventoryMovement (N)
```

- Un Business tiene muchos Products.
- Un Business tiene muchos InventoryMovements.
- Un Product tiene muchos InventoryMovements.
- Cada InventoryMovement pertenece a un Business y a un Product.

### 6.3 Entidad: Business

Campos: `_id`, `name`, `owner_name`, `phone`, `pin_hash` (agregado en la implementación para autenticación, no estaba en el diseño original), `subscription_status` (`trial`/`active`/`cancelled`), `trial_ends_at`, `created_at`, `updated_at`.

Consideraciones: una sola sucursal en el MVP, sin empleados ni roles, `business_id` aísla datos por negocio. El PIN vive en el propio `Business` en vez de una colección `users` separada porque, en el alcance actual, un negocio tiene un solo dueño.

### 6.4 Entidad: Product

Campos: `_id`, `business_id`, `name`, `name_normalized` (minúsculas sin acentos, para voz), `unit` (default `pieza`), `cost_price`, `sale_price`, `stock`, `min_stock_alert`, `is_active`, `created_at`, `updated_at`.

Consideraciones: `stock` es el inventario actual; `is_active` reemplaza eliminación física; `name_normalized` facilita resolución por voz; sin categorías ni proveedores en el MVP.

Estrategia de costo (MVP): último costo registrado — al registrar una compra con nuevo precio, `cost_price` se actualiza con ese valor. Sin promedio ponderado.

### 6.5 Entidad: InventoryMovement

El historial completo de entradas y salidas. El stock actual nunca se modifica sin crear un InventoryMovement.

Tipos: `sale`, `purchase`, `adjustment`.

Campos: `_id`, `business_id`, `product_id`, `type`, `quantity`, `unit_cost_snapshot`, `unit_sale_snapshot`, `total_amount`, `source` (`voice`/`manual`), `session_id` (opcional, sesión del agente), `reason` (opcional, agregado en la implementación — solo aplica a movimientos `adjustment`, ej. "merma"), `created_at`, `updated_at`.

Consideraciones: se usan snapshots para coherencia histórica; `source` distingue voz vs manual; `session_id` audita comandos del agente.

### 6.6 Cálculo de ganancia

```
Ganancia = (unit_sale_snapshot - unit_cost_snapshot) * quantity
```

Resumen diario: filtrar movimientos tipo `sale`, agrupar por fecha, sumar ganancia. Es una ganancia estimada, no contabilidad formal.

### 6.7 Reglas de negocio del MVP

1. El stock solo se modifica mediante un InventoryMovement.
2. Toda venta guarda snapshot de costo y precio.
3. El agente no modifica base de datos directamente (usa tools) — aplica desde que exista agente.
4. No existen proveedores en el MVP.
5. No existe contabilidad formal.
6. No se manejan múltiples sucursales.
7. El sistema prioriza simplicidad sobre precisión contable avanzada.

### 6.8 Modelo físico en MongoDB

Colección `businesses`:

```json
{
  "_id": "ObjectId",
  "name": "Abarrotes Lupita",
  "owner_name": "Don Jose",
  "phone": "5512345678",
  "subscription_status": "trial",
  "trial_ends_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

Colección `products`:

```json
{
  "_id": "ObjectId",
  "business_id": "ObjectId",
  "name": "Coca Cola 600ml",
  "name_normalized": "coca cola 600ml",
  "unit": "pieza",
  "cost_price": 10,
  "sale_price": 15,
  "stock": 24,
  "min_stock_alert": 5,
  "is_active": true,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

Índices recomendados: `{ business_id: 1 }`, `{ business_id: 1, name_normalized: 1 }`, `{ business_id: 1, is_active: 1 }`. El índice por `name_normalized` es clave para búsqueda por voz.

Colección `inventory_movements`:

```json
{
  "_id": "ObjectId",
  "business_id": "ObjectId",
  "product_id": "ObjectId",
  "type": "sale",
  "quantity": 3,
  "unit_cost_snapshot": 10,
  "unit_sale_snapshot": 15,
  "total_amount": 45,
  "source": "voice",
  "session_id": "session_abc123",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

Índices recomendados: `{ business_id: 1, created_at: -1 }`, `{ product_id: 1 }`, `{ type: 1 }`.

### 6.9 Decisiones arquitectónicas del modelo

- No se embeben movimientos dentro de Product.
- Se separa estado actual (Product) de historial (InventoryMovement).
- Redis maneja memoria del agente, no Mongo (fase posterior).
- Mongo guarda únicamente datos persistentes del negocio.
- Diseñado para soportar crecimiento futuro sin rediseño estructural.

### 6.10 Generalización: venta por pieza o a granel

El modelo original asumía que todo se vendía por pieza (abarrotes). Se generalizó para servir también a negocios que venden a granel (ej. un molino de masa que vende masa por kilo), sin perder soporte para venta por pieza.

Cambios sobre `Product` (sección 6.4):

- Nuevo campo `sale_type`: `"pieza"` | `"granel"`.
- El campo `unit` ahora depende de `sale_type`: si es `"pieza"`, siempre vale `"pieza"`; si es `"granel"`, debe ser `"kg"` o `"g"` (las únicas unidades soportadas por ahora — se puede ampliar a `"litro"`/`"ml"` si un negocio lo necesita).
- `stock`, `min_stock_alert`, y `quantity`/`delta_quantity` en movimientos pasan de entero a **decimal**, para poder vender fracciones (ej. "2.5 kg de masa"). Esto no rompe el caso de pieza: 3.0 piezas se comporta igual que 3.

Esto significa que `stockTotal` en `/summary` ahora solo suma productos `sale_type == "pieza"` (sumar piezas y kilos en un mismo número no tiene sentido).

### 6.11 Materia prima (nuevo, independiente de productos)

Inventario separado para insumos que un negocio compra pero no vende directamente (ej. maíz, cal, gas, bolsas). **Decisión explícita del negocio: no hay receta ni cálculo automático de costo de producto a partir de materia prima consumida** — son dos inventarios completamente independientes. Esto es intencional: simplifica el modelo y evita tener que mantener recetas por producto que en la práctica varían mucho (ej. la masa lleva sal, manteca, agua, en proporciones que no se miden con precisión en el negocio real).

Colección `raw_materials`:

```json
{
  "_id": "ObjectId",
  "business_id": "ObjectId",
  "name": "Maiz",
  "unit": "kg",
  "stock": 70,
  "is_active": true,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

`unit` es texto libre (no restringido a un enum) porque solo se usa para mostrarlo, no para lógica de negocio.

Colección `raw_material_movements`:

```json
{
  "_id": "ObjectId",
  "business_id": "ObjectId",
  "raw_material_id": "ObjectId",
  "type": "compra",
  "quantity": 100,
  "unit_cost": 12,
  "total_cost": 1200,
  "created_at": "ISODate"
}
```

Tipos: `"compra"` (aumenta stock, registra costo — de aquí salen los "egresos" del reporte quincenal) y `"consumo"` (disminuye stock, sin costo asociado — solo para saber cuánto queda). `consumo` no puede dejar el stock en negativo.

Endpoints: `GET/POST /raw-materials`, `PUT/DELETE /raw-materials/{id}`, `POST /raw-materials/{id}/purchases`, `POST /raw-materials/{id}/usage`.

### 6.12 Reporte quincenal (ingresos vs. egresos, desglose diario)

`GET /summary/quincena?fecha=YYYY-MM-DD` (fecha opcional, por defecto hoy). Calcula la quincena a la que pertenece esa fecha (días 1-15 o 16-fin de mes del calendario) y regresa el desglose día por día.

- **Ingresos** de un día = suma de `total_amount` de movimientos `sale` (ventas de producto) creados ese día.
- **Egresos** de un día = suma de `total_amount` de movimientos `purchase` (entradas de producto/mercancía) **+** suma de `total_cost` de movimientos `compra` de materia prima, creados ese día. Decisión explícita: los egresos incluyen ambos tipos de compra, para dar una foto completa de cuánto dinero sale del negocio — no solo materia prima.
- `ganancia` de un día = `ingresos - egresos` (una vista simple de flujo de caja, no un margen por producto).

La respuesta incluye totales de la quincena completa (`ingresosTotal`, `egresosTotal`, `gananciaTotal`) y el arreglo `dias` con el desglose, para que el frontend pueda mostrar el total primero y el detalle día por día como opción ("ver desglose").

---

## 7. Agente inteligente (LangChain) — fase posterior, NO en la primera entrega

> Todo lo de esta sección y la sección 8 se implementa cuando se agregue el registro por voz. Se documenta aquí para no perder el diseño ya definido.

### 7.1 Objetivo

Que el agente interprete comandos en lenguaje natural (texto ya transcrito desde voz), use memoria conversacional corta (Redis), cargue contexto dinámico del negocio (MongoDB), seleccione una tool de forma segura, ejecute la lógica real únicamente a través de tools, y responda con mensajes simples (nivel WhatsApp).

### 7.2 Arquitectura interna del agente

1. Prompt base (system prompt)
2. Context Loader (MongoDB → contexto del negocio)
3. Memory Manager (Redis → sesión corta)
4. Tool Router (LangChain → selecciona herramienta)

### 7.3 Input / Output del agente

Input por request: `business_id`, `session_id` (puede ser `business_id` al inicio), `message_text` (texto ya transcrito), `timestamp`.

Output esperado: `reply_text`, `action` (tool ejecutada o null), `tool_result` (objeto o null), `needs_clarification` (bool), `clarification_question` (string o null).

### 7.4 Memoria del agente (Redis)

Por sesión se guarda: `last_intent` (sale/purchase/stock/profit/adjustment), `last_product_id` (o nombre normalizado), `last_quantity`, `last_messages` (últimos 3–5), `last_updated_at`.

TTL recomendado: 30 minutos de inactividad.

Objetivo: permitir frases como "y 2 más", "lo mismo", "ahora de ese producto" sin repetir todo.

### 7.5 Context Loader (MongoDB)

Antes de decidir tool, se carga: lista de productos activos del negocio (id, nombre, stock, precio de venta, costo), fecha/hora actual (CDMX), y opcionalmente resumen del día (ventas de hoy, ganancia estimada hoy).

Regla de oro: el agente no debe inventar productos — se apoya en esta lista real para resolver alias ("cocas" → "Coca Cola 600ml").

### 7.6 Pipeline LangChain recomendado (por request)

1. Fetch memory (Redis)
2. Load business context (Mongo)
3. Build agent input (prompt + memoria + contexto + mensaje)
4. Agent decides (tool call o pregunta)
5. Execute tool (solo si hay parámetros completos)
6. Update memory (guardar último producto/intención)
7. Return response

Tipo de agente recomendado: agente con tools (function calling), estricto con validación de parámetros, sin RAG con embeddings todavía.

### 7.7 System prompt base

> Rol: Eres un asistente de inventario para dueños de abarrotes en CDMX.
> Objetivo: Ayudar a registrar ventas/compras/ajustes y responder consultas de stock o ganancia de forma simple.
>
> Reglas:
> 1. NO inventes productos. Solo usa los productos del contexto.
> 2. NO hagas cálculos ni cambios directamente. Para cambios usa tools.
> 3. Si falta información (producto, cantidad o precio cuando aplique), pregunta una sola cosa concreta.
> 4. Responde como WhatsApp: breve, claro, sin tecnicismos.
> 5. Confirma siempre lo ejecutado: producto, cantidad, stock restante o total estimado.
>
> Formato de salida: si vas a ejecutar una acción, llama a la tool correcta con parámetros completos. Si necesitas aclaración, responde con una pregunta directa.

### 7.8 Contratos de tools

**`register_sale`** — registra una venta y actualiza stock.
- Input: `business_id`, `product_id`, `quantity`, `created_by_voice`, `timestamp`.
- Validaciones: producto existe y pertenece al business, stock suficiente, `quantity > 0`.
- Acciones: crea `inventory_movement` tipo `sale`, resta stock, calcula ganancia con snapshots.
- Output: `movement_id`, `product_name`, `quantity`, `new_stock`, `profit_estimated`, `total_sale_amount`.

**`register_purchase`** — registra compra/entrada de mercancía.
- Input: `business_id`, `product_id`, `quantity`, `unit_cost` (opcional), `created_by_voice`, `timestamp`.
- Validaciones: `quantity > 0`.
- Acciones: crea `movement` tipo `purchase`, suma stock, si viene `unit_cost` actualiza `cost_price` (estrategia último costo).
- Output: `movement_id`, `product_name`, `quantity`, `new_stock`, `unit_cost_used`.

**`check_stock`** — consulta stock de un producto.
- Input: `business_id`, `product_id`.
- Output: `product_name`, `stock`, `min_stock_alert`, `is_low_stock`.

**`get_profit_summary`** — resumen de ganancia estimada en un rango.
- Input: `business_id`, `range` (`today`/`yesterday`/`this_week`/`custom`), `start_date`/`end_date` (opcionales).
- Output: `total_sales_amount`, `total_profit_estimated`, `num_sales`, `best_sale_day`/`worst_sale_day` (solo si es semana).

**`adjust_stock`** — ajuste manual por merma o error.
- Input: `business_id`, `product_id`, `delta_quantity` (positivo o negativo), `reason` (ej. "merma", "conteo", "error"), `created_by_voice`, `timestamp`.
- Acciones: crea `movement` tipo `adjustment`, actualiza stock sumando delta.
- Output: `movement_id`, `product_name`, `delta_quantity`, `new_stock`.

### 7.9 Resolución de producto (normalización)

Sin embeddings todavía:

1. Normalizar texto (minúsculas, sin acentos).
2. Buscar coincidencia exacta por nombre.
3. Si no hay exacta, buscar "contains" por palabras clave.
4. Si hay 2+ candidatos, pedir aclaración con opciones cortas (ej. "¿Te refieres a 'Coca Cola 600ml' o 'Coca Cola 355ml'?").

### 7.10 Manejo de ambigüedad

El agente pregunta cuando falta producto, cantidad, o precio de compra (si no se puede inferir). Nunca asume sin información suficiente.

### 7.11 Estilo de respuesta (WhatsApp)

Confirmación + datos clave, una sola línea si es posible, sin tecnicismos. Ejemplos: "Listo ✅ Vendiste 3 Coca Cola 600ml. Te quedan 12.", "Hecho ✅ Entraron 20 Sabritas. Stock: 35.", "Hoy llevas $420 de ganancia estimada y 18 ventas."

### 7.12 Seguridad y control

1. El agente no escribe directo en Mongo, solo a través de tools.
2. Las tools validan `business_id`, ownership del producto, y stock suficiente.
3. Si una tool falla, el agente responde con mensaje claro y acción sugerida (ej. "Ups, no tienes suficiente stock de Coca Cola. Te quedan 2.").

### 7.13 Casos de prueba mínimos

- Ventas: "Vendí 3 cocas", "Y 2 más" (usa memoria), "Vendí 10 sabritas" (stock insuficiente).
- Compras: "Compré 20 cocas", "Compré 20 cocas a 11 pesos" (actualiza `cost_price`).
- Consultas: "¿Cuántas cocas me quedan?", "¿Cuánto gané hoy?".
- Ajustes: "Se me echaron a perder 2 leches" (adjustment -2, reason merma).

### 7.14 Evolución futura (no MVP)

Embeddings para matching de producto (vector search), memoria persistente de largo plazo, clasificador de intención más robusto, multimodal (foto de ticket/anaquel).

---

## 8. Flujo de registro por voz — fase posterior, NO en la primera entrega

### 8.1 Principio central

El usuario habla de forma natural, como un audio de WhatsApp. El sistema entiende intención, identifica producto, detecta cantidad, ejecuta la acción correcta y confirma el resultado.

### 8.2 Componentes que participan

Usuario, Frontend Web, Speech-to-Text, Backend FastAPI, Agente LangChain, Redis, MongoDB, Tools.

### 8.3 Flujo general

```
Usuario habla
   ↓
Speech-to-Text convierte audio a texto
   ↓
Backend recibe texto
   ↓
Agente analiza intencion
   ↓
Consulta memoria (Redis)
   ↓
Carga contexto del negocio (MongoDB)
   ↓
Selecciona Tool
   ↓
Tool ejecuta logica real
   ↓
Se actualiza base de datos
   ↓
Agente genera respuesta natural
   ↓
Frontend muestra confirmacion
```

### 8.4 Cómo "piensa" el agente

1. **Analizar intención**: sale / purchase / stock / profit / adjustment.
2. **Extraer entidades**: producto, cantidad, precio, fecha (ej. "Vendí 3 cocas" → intención `sale`, producto Coca Cola, cantidad 3).
3. **Consultar memoria (Redis)**: último producto, última intención, últimos mensajes (ej. "Vendí 3 cocas" → "Y 2 más" se resuelve con memoria).
4. **Cargar contexto del negocio**: lista de productos, stock actual, fecha, movimientos recientes.
5. **Seleccionar tool**: nunca se modifica la base de datos directamente.
6. **Ejecutar tool**: valida reglas, actualiza stock, crea InventoryMovement, calcula ganancia. La lógica vive en la tool, no en el LLM.
7. **Generar respuesta natural**: clara, simple, sin tecnicismos.

### 8.5 Ejemplos de flujo real

- **Venta directa**: "Vendí 5 sabritas" → detecta intención, identifica producto, resta stock, guarda movimiento, confirma.
- **Venta con memoria**: "Vendí 3 cocas" → "Y 2 más" → usa memoria Redis, ejecuta nueva venta, confirma acumulado.
- **Consulta de ganancia**: "¿Cuánto llevo hoy?" → consulta movimientos `sale` del día, calcula ganancia, responde resumen.

### 8.6 Manejo de ambigüedad

Si el agente no entiende, pregunta. Ejemplo: "Vendí 3" → "¿De qué producto?". Nunca asume sin información suficiente.

### 8.7 Reglas de seguridad del agente

1. El LLM no modifica datos directamente.
2. Toda modificación pasa por tools.
3. Se valida stock antes de vender.
4. Se evita ejecución sin parámetros completos.
5. Si no hay producto existente, se solicita confirmación.

### 8.8 Tiempo de respuesta objetivo

STT: 1–2s. Agente + tool: 1–2s. Total ideal: menos de 4 segundos.

### 8.9 Métricas de validación del flujo

% de comandos correctamente interpretados, % de uso por voz vs manual, número promedio de registros diarios, errores de interpretación, tiempo promedio de respuesta.

### 8.10 Diseño de memoria (Redis)

Por sesión: último producto, última intención, últimos 3–5 mensajes, timestamp. TTL: 30 minutos de inactividad; al expirar, la sesión se limpia sola.

### 8.11 Qué NO hace el agente

No calcula contabilidad formal, no toma decisiones financieras complejas, no predice compras futuras (en MVP), no maneja múltiples negocios en la misma sesión.

### 8.12 Principio final

El sistema debe sentirse como "un asistente que entiende cómo hablo", no como "un sistema que me obliga a hablar estructurado".

---

## 9. Qué NO incluye esta arquitectura (ningún MVP)

- SAT / facturación electrónica
- Sistema POS completo
- Multi-sucursal
- Permisos complejos
- Contabilidad formal
- Integraciones bancarias
- Microservicios

## 10. Arquitectura orientada a validación (Sprint 0)

Permite medir: número de movimientos por negocio, frecuencia semanal de uso, % de registros por voz, retención semanal, ganancia estimada diaria.

Meta mínima: 5 negocios activos, 3 pagos reales, 20 registros por voz por semana.

Meta ideal: 10–15 activos, 7–10 pagos, $3,000–$6,000 MXN MRR, 70% de uso por voz.

## 11. Decisión estratégica final

Validar primero, escalar después.

Si se valida el producto: migrar a arquitectura distribuida, separar el agente en microservicio, implementar serverless híbrido, escalar infraestructura.

Si no se valida: ajustar nicho o propuesta sin haber sobreinvertido en infraestructura.
