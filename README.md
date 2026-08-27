# S-Pback

API del agente de inventario para abarrotes de colonia en CDMX: productos, movimientos de stock (entradas/ventas), stock en tiempo real y ganancia estimada.

Frontend: [SAAS-PYMES](https://github.com/EraRamirez/SAAS-PYMES)

## Stack

- Node 20 + TypeScript
- Hono
- PostgreSQL + Drizzle ORM
- Zod para validacion
- JWT + PIN (telefono + PIN, sin Cognito)

## Modelo de datos

`businesses` -> `users`, `products`, `movements`. Un dueno = un negocio = un inventario.

## Desarrollo local

```bash
cp .env.example .env
# edita DATABASE_URL con tu Postgres (ej. Supabase) y JWT_SECRET
npm install
npm run db:generate   # genera la migracion a partir del schema
npm run db:migrate    # aplica la migracion
npm run dev           # levanta la API en http://localhost:8787
```

## Endpoints

- `POST /auth/register` - crea negocio + usuario
- `POST /auth/login` - telefono + pin -> token
- `GET /products` / `POST /products` / `PUT /products/:id` / `DELETE /products/:id`
- `POST /movements` - registra entrada o venta (actualiza stock)
- `GET /summary` - stock total, ganancia hoy/semana, productos bajo inventario

Cuando vuelva la voz: `POST /voice` transcribe y escribe en `movements` sin cambiar el modelo.
