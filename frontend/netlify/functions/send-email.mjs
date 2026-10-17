// Email relay for the MindEase backend.
//
// Render's free plan blocks outbound SMTP, so the backend can't talk to Gmail directly.
// Netlify Functions can, so the backend POSTs the finished message here over HTTPS and
// this function sends it through Gmail with Nodemailer.
//
// Netlify env vars (Site configuration -> Environment variables):
//   GMAIL_USER          the Gmail address that sends the codes
//   GMAIL_APP_PASSWORD  a 16-character Google App Password (not the normal password)
//   EMAIL_RELAY_SECRET  long random string; must equal EMAIL_RELAY_SECRET on Render
//   MAIL_FROM_NAME      optional display name, defaults to "MindEase"
import crypto from "node:crypto";
import nodemailer from "nodemailer";

const json = (status, body) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function secretMatches(header) {
  const expected = process.env.EMAIL_RELAY_SECRET || "";
  const given = (header || "").replace(/^Bearer\s+/i, "");
  if (!expected || given.length !== expected.length) return false;
  return crypto.timingSafeEqual(Buffer.from(given), Buffer.from(expected));
}

let transporter;
function getTransporter() {
  transporter ??= nodemailer.createTransport({
    service: "gmail",
    auth: { user: process.env.GMAIL_USER, pass: process.env.GMAIL_APP_PASSWORD },
  });
  return transporter;
}

export default async (req) => {
  if (req.method !== "POST") return json(405, { error: "Method not allowed" });
  // Only the backend knows the secret, so this can't be used to send arbitrary spam.
  if (!secretMatches(req.headers.get("authorization"))) return json(401, { error: "Unauthorized" });
  if (!process.env.GMAIL_USER || !process.env.GMAIL_APP_PASSWORD) {
    return json(500, { error: "GMAIL_USER / GMAIL_APP_PASSWORD are not set on Netlify" });
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: "Expected a JSON body" });
  }
  const { to, toName, subject, text, html } = body ?? {};
  if (typeof to !== "string" || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(to) || typeof subject !== "string" || typeof text !== "string") {
    return json(400, { error: "to, subject and text are required" });
  }
  if (subject.length > 200 || text.length > 20000 || (html && html.length > 100000)) {
    return json(413, { error: "Message too large" });
  }

  try {
    const info = await getTransporter().sendMail({
      from: { name: process.env.MAIL_FROM_NAME || "MindEase", address: process.env.GMAIL_USER },
      to: toName ? { name: String(toName).slice(0, 100), address: to } : to,
      subject,
      text,
      html: typeof html === "string" ? html : undefined,
    });
    return json(200, { ok: true, messageId: info.messageId });
  } catch (err) {
    // e.g. 535 "Username and Password not accepted" when the App Password is wrong.
    return json(502, { error: `Gmail rejected the message: ${err.message}` });
  }
};
