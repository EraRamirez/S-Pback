import 'dotenv/config'
import { serve } from '@hono/node-server'
import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { authRoutes } from './routes/auth'
import { movementsRoutes } from './routes/movements'
import { productsRoutes } from './routes/products'
import { summaryRoutes } from './routes/summary'

const app = new Hono()

app.use('*', cors())

app.get('/health', (c) => c.json({ ok: true }))

app.route('/auth', authRoutes)
app.route('/products', productsRoutes)
app.route('/movements', movementsRoutes)
app.route('/summary', summaryRoutes)

const port = Number(process.env.PORT ?? 8787)

serve({ fetch: app.fetch, port }, (info) => {
  console.log(`API lista en http://localhost:${info.port}`)
})
