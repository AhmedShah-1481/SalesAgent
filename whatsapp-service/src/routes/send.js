import { Router } from "express";

import { getSock, isConnected } from "../baileys.js";

const router = Router();

// Turn a raw number (or +number, or a full JID) into a WhatsApp JID.
function toJid(to) {
  const raw = String(to);
  if (raw.includes("@")) return raw;
  const digits = raw.replace(/[^\d]/g, "");
  return `${digits}@s.whatsapp.net`;
}

// POST /send-whatsapp { to, message }
// Sends via Baileys when connected; 503 until the QR is scanned (backend degrades to a log).
router.post("/send-whatsapp", async (req, res) => {
  const { to, message } = req.body || {};
  if (!to || !message) {
    return res.status(400).json({ error: "Body must include { to, message }." });
  }

  const sock = getSock();
  if (!sock || !isConnected()) {
    return res.status(503).json({
      error: "WhatsApp not connected — scan the QR code shown in the service logs.",
      received: { to, messagePreview: String(message).slice(0, 40) },
    });
  }

  try {
    const jid = toJid(to);
    const result = await sock.sendMessage(jid, { text: String(message) });
    return res.json({ status: "sent", to: jid, id: result?.key?.id || null });
  } catch (err) {
    return res.status(502).json({ error: `Send failed: ${err.message}` });
  }
});

export default router;
