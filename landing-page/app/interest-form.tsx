"use client";
import { FormEvent, useState } from "react";

export function InterestForm() {
  const [state, setState] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  async function submitInterest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setState("submitting"); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/interest", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ email: form.get("email"), consent: form.get("consent") === "yes", website: form.get("website") }) });
      const result = (await response.json()) as { message?: string };
      if (!response.ok) throw new Error(result.message || "Please try again.");
      event.currentTarget.reset(); setState("success"); setMessage(result.message || "You’re on the list.");
    } catch (error) { setState("error"); setMessage(error instanceof Error ? error.message : "Please try again."); }
  }
  return <form className="interest-form" onSubmit={submitInterest}>
    <div className="field"><label htmlFor="interest-email">Work or personal email</label><input id="interest-email" name="email" type="email" autoComplete="email" inputMode="email" placeholder="you@example.com" maxLength={320} required /></div>
    <div className="website-field" aria-hidden="true"><label htmlFor="website">Website</label><input id="website" name="website" type="text" tabIndex={-1} autoComplete="off" /></div>
    <label className="consent"><input name="consent" type="checkbox" value="yes" required /><span>I’d like Jean Nathan Tshibuyi to email me occasional Memory Seed product updates, research invitations, and early-access opportunities.</span></label>
    <button className="button button-primary submit-button" type="submit" disabled={state === "submitting"}>{state === "submitting" ? "Joining…" : "Join the early-access list"}</button>
    <p className="form-privacy">Unsubscribe at any time. Read the <a href="/privacy">privacy notice</a>.</p><p className={`form-status ${state}`} role="status" aria-live="polite">{message}</p>
  </form>;
}
