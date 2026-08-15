// Baileys WhatsApp connection — Phase 9.
// The baileys import is DYNAMIC (inside the function) so nothing heavy loads at boot.
// useMultiFileAuthState persists the session under ./auth so reconnects don't require
// re-scanning the QR. Inbound messages are forwarded to the Python backend over HTTP
// (the only Node -> Python seam); the backend classifies them (§10).
import path from "node:path";
import { fileURLToPath } from "node:url";

import pino from "pino";
import qrcode from "qrcode-terminal";

import { forwardInbound } from "./forwarder.js";

const logger = pino({ level: process.env.LOG_LEVEL || "info" });

let sock = null;
let connected = false;

export function getSock() {
  return sock;
}

export function isConnected() {
  return connected;
}

function extractText(message) {
  return (
    message.conversation ||
    message.extendedTextMessage?.text ||
    message.imageMessage?.caption ||
    message.videoMessage?.caption ||
    ""
  );
}

export async function connectToWhatsApp() {
  const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = await import(
    "@whiskeysockets/baileys"
  );

  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const authDir = path.resolve(__dirname, "../auth");
  const { state, saveCreds } = await useMultiFileAuthState(authDir);

  sock = makeWASocket({ auth: state, logger: pino({ level: "silent" }) });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      logger.info("Scan this QR code with WhatsApp (Linked devices) to connect:");
      qrcode.generate(qr, { small: true });
    }
    if (connection === "open") {
      connected = true;
      logger.info("WhatsApp connected — sending + inbound forwarding are live.");
    }
    if (connection === "close") {
      connected = false;
      const loggedOut = lastDisconnect?.error?.output?.statusCode === DisconnectReason.loggedOut;
      if (loggedOut) {
        logger.warn("Logged out. Delete the auth/ folder and restart to re-scan the QR.");
      } else {
        logger.warn("Connection closed — reconnecting...");
        connectToWhatsApp();
      }
    }
  });

  // Forward inbound prospect messages to the backend classifier (§10).
  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    for (const m of messages) {
      const jid = m.key?.remoteJid || "";
      // Skip our own messages, groups, and status broadcasts.
      if (!m.message || m.key?.fromMe) continue;
      if (jid.endsWith("@g.us") || jid === "status@broadcast") continue;

      const text = extractText(m.message);
      if (!text) continue;

      const phone = jid.split("@")[0].split(":")[0];
      try {
        await forwardInbound({
          from: jid,
          phone,
          text,
          pushName: m.pushName || "",
          messageId: m.key?.id || "",
        });
        logger.info(`Forwarded inbound WhatsApp from ${phone}.`);
      } catch (err) {
        logger.error(`Failed to forward inbound message: ${err.message}`);
      }
    }
  });

  return sock;
}
