import { and, eq } from 'drizzle-orm'
import { Hono } from 'hono'
import { z } from 'zod'
import { db } from '../db/client'
import { products } from '../db/schema'
import { authMiddleware, type AppEnv } from '../lib/auth'

export const productsRoutes = new Hono<AppEnv>()

productsRoutes.use('*', authMiddleware)

productsRoutes.get('/', async (c) => {
  const auth = c.get('auth')
  const rows = await db.select().from(products).where(eq(products.businessId, auth.businessId))
  return c.json(rows)
})

const upsertSchema = z.object({
  nombre: z.string().min(1),
  costo: z.number().nonnegative(),
  precio: z.number().nonnegative(),
  cantidad: z.number().int().nonnegative(),
  cantidadMinima: z.number().int().nonnegative().default(0),
})

productsRoutes.post('/', async (c) => {
  const auth = c.get('auth')
  const body = upsertSchema.parse(await c.req.json())

  const [product] = await db
    .insert(products)
    .values({
      businessId: auth.businessId,
      nombre: body.nombre,
      costo: body.costo.toFixed(2),
      precio: body.precio.toFixed(2),
      cantidad: body.cantidad,
      cantidadMinima: body.cantidadMinima,
    })
    .returning()

  return c.json(product, 201)
})

productsRoutes.put('/:id', async (c) => {
  const auth = c.get('auth')
  const id = c.req.param('id')
  const body = upsertSchema.partial().parse(await c.req.json())

  const [product] = await db
    .update(products)
    .set({
      ...(body.nombre !== undefined ? { nombre: body.nombre } : {}),
      ...(body.costo !== undefined ? { costo: body.costo.toFixed(2) } : {}),
      ...(body.precio !== undefined ? { precio: body.precio.toFixed(2) } : {}),
      ...(body.cantidad !== undefined ? { cantidad: body.cantidad } : {}),
      ...(body.cantidadMinima !== undefined ? { cantidadMinima: body.cantidadMinima } : {}),
    })
    .where(and(eq(products.id, id), eq(products.businessId, auth.businessId)))
    .returning()

  if (!product) return c.json({ message: 'Producto no encontrado' }, 404)
  return c.json(product)
})

productsRoutes.delete('/:id', async (c) => {
  const auth = c.get('auth')
  const id = c.req.param('id')

  await db.delete(products).where(and(eq(products.id, id), eq(products.businessId, auth.businessId)))
  return c.body(null, 204)
})
