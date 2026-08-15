// Isolated WhatsApp microservice — Express entrypoint.
// Phase 9: boots, serves /health + /send-whatsapp, and opens the Baileys session
// (scan the QR shown in the logs). Inbound messages are forwarded to the Python
// backend's /whatsapp-incoming webhook. Talks to Python ONLY over plain HTTP.
import path from "node:path";
import { fileURLToPath } from "node:url";

import dotenv from "dotenv";
import express from "express";
import pino from "pino";

import { connectToWhatsApp } from "./baileys.js";
import healthRouter from "./routes/health.js";
import sendRouter from "./routes/send.js";

// Load the repo-root .env (single source of truth), then any local override.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, "../../.env") });
dotenv.config({ path: path.resolve(__dirname, "../.env") });

const logger = pino({ level: process.env.LOG_LEVEL || "info" });

const app = express();
app.use(express.json());
app.use(healthRouter);
app.use(sendRouter);

const PORT = process.env.WHATSAPP_PORT || 3001;
app.listen(PORT, () => {
  logger.info(`WhatsApp microservice listening on http://localhost:${PORT}`);
  // Open the WhatsApp session (prints a QR to scan on first run). Best-effort: the
  // service still serves /health and returns 503 from /send-whatsapp until connected.
  connectToWhatsApp().catch((err) => {
    logger.error(`Failed to start WhatsApp connection: ${err.message}`);
  });
});

