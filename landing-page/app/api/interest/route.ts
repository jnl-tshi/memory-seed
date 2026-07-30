import { env } from "cloudflare:workers";
import { NextResponse } from "next/server";
const CONSENT_VERSION = "interest-v1-2026-07-30";
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function ensureSchema() {
  await env.DB.batch([
    env.DB.prepare("CREATE TABLE IF NOT EXISTS interests (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, consented_at TEXT NOT NULL, consent_version TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"),
    env.DB.prepare("CREATE INDEX IF NOT EXISTS interests_status_idx ON interests (status)"),
  ]);
}
export async function POST(request: Request) {
  let body: { email?: unknown; consent?: unknown; website?: unknown };
  try { body = await request.json(); } catch { return NextResponse.json({ message: "Please enter a valid email address." }, { status: 400 }); }
  if (typeof body.website === "string" && body.website.trim()) return NextResponse.json({ message: "Thanks—your interest has been recorded." });
  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
  if (!email || email.length > 320 || !EMAIL_PATTERN.test(email)) return NextResponse.json({ message: "Please enter a valid email address." }, { status: 400 });
  if (body.consent !== true) return NextResponse.json({ message: "Please confirm that you want to receive these emails." }, { status: 400 });
  const now = new Date().toISOString();
  try {
    await ensureSchema();
    await env.DB.prepare("INSERT INTO interests (email, consented_at, consent_version, source, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'active', ?, ?) ON CONFLICT(email) DO UPDATE SET consented_at = excluded.consented_at, consent_version = excluded.consent_version, source = excluded.source, status = 'active', updated_at = excluded.updated_at").bind(email, now, CONSENT_VERSION, "landing-page", now, now).run();
    return NextResponse.json({ message: "You’re on the list. Thanks for helping shape Memory Seed." });
  } catch { return NextResponse.json({ message: "We couldn’t save your interest just now. Please try again." }, { status: 500 }); }
}
