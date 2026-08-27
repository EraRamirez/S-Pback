import { and, eq, gte, sql, sum } from 'drizzle-orm'
import { Hono } from 'hono'
import { db } from '../db/client'
import { movements, products } from '../db/schema'
import { authMiddleware, type AppEnv } from '../lib/auth'

export const summaryRoutes = new Hono<AppEnv>()

summaryRoutes.use('*', authMiddleware)

async function gananciaDesde(businessId: string, since: Date) {
  const [row] = await db
    .select({
      total: sum(
        sql<number>`(${movements.precioUnitario} - ${products.costo}) * ${movements.cantidad}`,
      ),
    })
    .from(movements)
    .innerJoin(products, eq(movements.productId, products.id))
    .where(
      and(
        eq(movements.businessId, businessId),
        eq(movements.tipo, 'venta'),
        gte(movements.createdAt, since),
      ),
    )

  return Number(row?.total ?? 0)
}

summaryRoutes.get('/', async (c) => {
  const auth = c.get('auth')

  const startOfDay = new Date()
  startOfDay.setHours(0, 0, 0, 0)

  const startOfWeek = new Date()
  startOfWeek.setDate(startOfWeek.getDate() - 7)

  const [stockRow] = await db
    .select({ total: sum(products.cantidad) })
    .from(products)
    .where(eq(products.businessId, auth.businessId))

  const [gananciaHoy, gananciaSemana, productosBajoInventario] = await Promise.all([
    gananciaDesde(auth.businessId, startOfDay),
    gananciaDesde(auth.businessId, startOfWeek),
    db
      .select()
      .from(products)
      .where(
        and(eq(products.businessId, auth.businessId), sql`${products.cantidad} <= ${products.cantidadMinima}`),
      ),
  ])

  return c.json({
    stockTotal: Number(stockRow?.total ?? 0),
    gananciaHoy,
    gananciaSemana,
    productosBajoInventario: productosBajoInventario.map((p) => ({
      id: p.id,
      nombre: p.nombre,
      cantidad: p.cantidad,
    })),
  })
})
