import { and, eq, sql } from 'drizzle-orm'
import { Hono } from 'hono'
import { z } from 'zod'
import { db } from '../db/client'
import { movements, products } from '../db/schema'
import { authMiddleware, type AppEnv } from '../lib/auth'

export const movementsRoutes = new Hono<AppEnv>()

movementsRoutes.use('*', authMiddleware)

const movementSchema = z.object({
  productId: z.string().uuid(),
  tipo: z.enum(['entrada', 'venta']),
  cantidad: z.number().int().positive(),
  precioUnitario: z.number().nonnegative(),
})

movementsRoutes.post('/', async (c) => {
  const auth = c.get('auth')
  const body = movementSchema.parse(await c.req.json())

  const product = await db.query.products.findFirst({
    where: and(eq(products.id, body.productId), eq(products.businessId, auth.businessId)),
  })
  if (!product) return c.json({ message: 'Producto no encontrado' }, 404)

  if (body.tipo === 'venta' && product.cantidad < body.cantidad) {
    return c.json({ message: 'No hay suficiente stock' }, 400)
  }

  const delta = body.tipo === 'entrada' ? body.cantidad : -body.cantidad

  const movement = await db.transaction(async (tx) => {
    const [inserted] = await tx
      .insert(movements)
      .values({
        businessId: auth.businessId,
        productId: body.productId,
        tipo: body.tipo,
        cantidad: body.cantidad,
        precioUnitario: body.precioUnitario.toFixed(2),
      })
      .returning()

    await tx
      .update(products)
      .set({ cantidad: sql`${products.cantidad} + ${delta}` })
      .where(eq(products.id, body.productId))

    return inserted
  })

  return c.json(movement, 201)
})
