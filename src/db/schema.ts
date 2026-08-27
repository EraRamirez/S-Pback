import { relations } from 'drizzle-orm'
import { integer, numeric, pgEnum, pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core'

export const movementTypeEnum = pgEnum('movement_type', ['entrada', 'venta'])

export const businesses = pgTable('businesses', {
  id: uuid('id').primaryKey().defaultRandom(),
  nombre: text('nombre').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  businessId: uuid('business_id')
    .notNull()
    .references(() => businesses.id),
  telefono: text('telefono').notNull().unique(),
  pinHash: text('pin_hash').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const products = pgTable('products', {
  id: uuid('id').primaryKey().defaultRandom(),
  businessId: uuid('business_id')
    .notNull()
    .references(() => businesses.id),
  nombre: text('nombre').notNull(),
  costo: numeric('costo', { precision: 10, scale: 2 }).notNull(),
  precio: numeric('precio', { precision: 10, scale: 2 }).notNull(),
  cantidad: integer('cantidad').notNull().default(0),
  cantidadMinima: integer('cantidad_minima').notNull().default(0),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const movements = pgTable('movements', {
  id: uuid('id').primaryKey().defaultRandom(),
  businessId: uuid('business_id')
    .notNull()
    .references(() => businesses.id),
  productId: uuid('product_id')
    .notNull()
    .references(() => products.id),
  tipo: movementTypeEnum('tipo').notNull(),
  cantidad: integer('cantidad').notNull(),
  precioUnitario: numeric('precio_unitario', { precision: 10, scale: 2 }).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const businessesRelations = relations(businesses, ({ many }) => ({
  users: many(users),
  products: many(products),
  movements: many(movements),
}))

export const productsRelations = relations(products, ({ one, many }) => ({
  business: one(businesses, { fields: [products.businessId], references: [businesses.id] }),
  movements: many(movements),
}))

export const movementsRelations = relations(movements, ({ one }) => ({
  business: one(businesses, { fields: [movements.businessId], references: [businesses.id] }),
  product: one(products, { fields: [movements.productId], references: [products.id] }),
}))
