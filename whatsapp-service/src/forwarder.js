// Forward an inbound WhatsApp message to the Python backend webhook — Phase 9.
// This is the ONLY way the Node service talks to Python: a plain HTTP POST.
import axios from "axios";

export async function forwardInbound(payload) {
  const backend = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
  const url = `${backend}/whatsapp-incoming`;
  const { data } = await axios.post(url, payload, { timeout: 15000 });
  return data;
}
