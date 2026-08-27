# S-Pback

API del agente de inventario para abarrotes de colonia en CDMX: productos, movimientos de stock (entradas/ventas/ajustes), stock en tiempo real y ganancia estimada.

Frontend: [SAAS-PYMES](https://github.com/EraRamirez/SAAS-PYMES)

Arquitectura completa (modelo de datos, agente, flujo de voz): [ARQUITECTURA.md](ARQUITECTURA.md)

## Stack

- Python 3.12 + FastAPI
- MongoDB (via Motor, driver async)
- Pydantic / pydantic-settings para validacion y configuracion
- JWT (python-jose) + PIN hasheado con bcrypt (telefono + PIN, sin Cognito)
- Docker / docker-compose para desarrollo local

## Modelo de datos

Colecciones `businesses`, `products`, `inventory_movements`. Un dueno = un negocio = un inventario. Detalle completo en [ARQUITECTURA.md](ARQUITECTURA.md#6-modelo-de-datos-mvp).

## Desarrollo local

Con Docker (API + MongoDB):

```bash
cp .env.example .env
docker compose up --build
```

Sin Docker (requiere un MongoDB accesible, ej. local o Atlas free tier):

```bash
cp .env.example .env
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
# edita .env con tu MONGODB_URI si no usas localhost:27017
.venv/bin/uvicorn app.main:app --reload --port 8787
```

La API queda en `http://localhost:8787`, docs interactivas en `http://localhost:8787/docs`.

## Tests

Usan `mongomock-motor` (Mongo simulado en memoria), no requieren base de datos real:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Endpoints

- `POST /auth/register` - crea negocio + owner (telefono + PIN)
- `POST /auth/login` - telefono + pin -> token
- `GET /products` / `POST /products` / `PUT /products/{id}` / `DELETE /products/{id}` (borrado logico)
- `POST /movements/sale` - registra venta (valida stock, actualiza inventario)
- `POST /movements/purchase` - registra entrada (actualiza stock y costo si se manda `unit_cost`)
- `POST /movements/adjustment` - ajuste manual (merma, conteo, error)
- `GET /summary` - stock total, ganancia hoy/semana, productos bajo inventario

Estas rutas espejean 1:1 los "tool contracts" del agente (`register_sale`, `register_purchase`, `adjust_stock`, `check_stock`, `get_profit_summary`) documentados en `ARQUITECTURA.md` — la logica vive en `app/services/movements.py`, lista para ser envuelta como tools de LangChain cuando llegue la fase de voz.

## Fuera de alcance en esta entrega

Registro por voz, Speech-to-Text, agente LangChain y memoria Redis — ver seccion 0 y 7-8 de [ARQUITECTURA.md](ARQUITECTURA.md).
