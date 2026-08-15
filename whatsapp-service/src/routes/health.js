import { Router } from "express";

import { isConnected } from "../baileys.js";

const router = Router();

router.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "whatsapp-service",
    phase: "9-whatsapp-live",
    connected: isConnected(),
  });
});

export default router;
