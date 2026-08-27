import bcrypt from 'bcryptjs'
import { eq } from 'drizzle-orm'
import { Hono } from 'hono'
import { z } from 'zod'
import { db } from '../db/client'
import { businesses, users } from '../db/schema'
import { signToken } from '../lib/auth'

export const authRoutes = new Hono()

const registerSchema = z.object({
  nombreNegocio: z.string().min(1),
  telefono: z.string().min(10),
  pin: z.string().min(4).max(6),
})

authRoutes.post('/register', async (c) => {
  const body = registerSchema.parse(await c.req.json())

  const existing = await db.query.users.findFirst({ where: eq(users.telefono, body.telefono) })
  if (existing) {
    return c.json({ message: 'Ese telefono ya esta registrado' }, 409)
  }

  const pinHash = await bcrypt.hash(body.pin, 10)

  const [business] = await db.insert(businesses).values({ nombre: body.nombreNegocio }).returning()
  const [user] = await db
    .insert(users)
    .values({ businessId: business.id, telefono: body.telefono, pinHash })
    .returning()

  const token = signToken({ userId: user.id, businessId: business.id })
  return c.json({ token })
})

const loginSchema = z.object({
  telefono: z.string().min(10),
  pin: z.string().min(4).max(6),
})

authRoutes.post('/login', async (c) => {
  const body = loginSchema.parse(await c.req.json())

  const user = await db.query.users.findFirst({ where: eq(users.telefono, body.telefono) })
  if (!user) {
    return c.json({ message: 'Telefono o PIN incorrecto' }, 401)
  }

  const valid = await bcrypt.compare(body.pin, user.pinHash)
  if (!valid) {
    return c.json({ message: 'Telefono o PIN incorrecto' }, 401)
  }

  const token = signToken({ userId: user.id, businessId: user.businessId })
  return c.json({ token })
})
