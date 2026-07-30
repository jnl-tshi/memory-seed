import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const interests = sqliteTable("interests", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  email: text("email").notNull().unique(),
  consentedAt: text("consented_at").notNull(),
  consentVersion: text("consent_version").notNull(),
  source: text("source").notNull(),
  status: text("status").notNull().default("active"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
}, (table) => [index("interests_status_idx").on(table.status)]);
