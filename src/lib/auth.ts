import jwt from 'jsonwebtoken'
import type { Context, Next } from 'hono'

const JWT_SECRET = process.env.JWT_SECRET ?? 'change-me'

export type TokenPayload = {
  userId: string
  businessId: string
}

export type AppEnv = {
  Variables: {
    auth: TokenPayload
  }
}

export function signToken(payload: TokenPayload) {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '30d' })
}

export function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, JWT_SECRET) as TokenPayload
}

export async function authMiddleware(c: Context<AppEnv>, next: Next) {
  const header = c.req.header('Authorization')
  const token = header?.startsWith('Bearer ') ? header.slice(7) : null

  if (!token) {
    return c.json({ message: 'No autorizado' }, 401)
  }

  try {
    const payload = verifyToken(token)
    c.set('auth', payload)
    await next()
  } catch {
    return c.json({ message: 'Token invalido' }, 401)
  }
}
