/**
 * Login page — phone OTP authentication (OL-146).
 *
 * Step 1: Phone input (E.164, India-first)
 * Step 2: 6-digit OTP verification
 * On success: store tokens, redirect to daily brief.
 *
 * DESIGN.md: DM Sans + JetBrains Mono, #F5F2EC bg, #1A4FBF accent.
 */

import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { fonts } from "@openlnk/ui";
import { useAppStore } from "../store/app";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

type Step = "phone" | "otp";

export default function LoginPage() {
  const { login } = useAppStore();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("+91");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSendOtp = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_e164: phone }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Failed (${res.status})`);
      }
      setStep("otp");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_e164: phone, otp }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Verification failed (${res.status})`);
      }
      const tokens = await res.json();
      login(tokens.access_token, tokens.refresh_token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Box
        sx={{
          width: 360,
          bgcolor: "background.paper",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "2px",
          p: 4,
        }}
      >
        <Typography
          sx={{
            fontFamily: fonts.mono,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "0.08em",
            color: "primary.main",
            mb: 3,
            textAlign: "center",
          }}
        >
          OPENLNK
        </Typography>

        {step === "phone" && (
          <>
            <Typography sx={{ fontSize: 14, mb: 2, color: "text.secondary" }}>
              Enter your phone number to sign in
            </Typography>
            <TextField
              fullWidth
              size="small"
              label="Phone (E.164)"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+919876543210"
              sx={{ mb: 2 }}
              slotProps={{ htmlInput: { inputMode: "tel" } }}
            />
            <Button
              variant="contained"
              fullWidth
              disabled={loading || phone.length < 10}
              onClick={handleSendOtp}
            >
              {loading ? "Sending..." : "Send OTP"}
            </Button>
          </>
        )}

        {step === "otp" && (
          <>
            <Typography sx={{ fontSize: 14, mb: 0.5, color: "text.secondary" }}>
              Enter the 6-digit code sent to
            </Typography>
            <Typography
              sx={{
                fontFamily: fonts.mono,
                fontSize: 13,
                mb: 2,
                color: "text.primary",
              }}
            >
              {phone}
            </Typography>
            <TextField
              fullWidth
              size="small"
              label="OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
              slotProps={{ htmlInput: { inputMode: "numeric", maxLength: 6, autoFocus: true } }}
              sx={{ mb: 2 }}
            />
            <Button
              variant="contained"
              fullWidth
              disabled={loading || otp.length !== 6}
              onClick={handleVerifyOtp}
            >
              {loading ? "Verifying..." : "Verify"}
            </Button>
            <Button
              variant="text"
              size="small"
              fullWidth
              onClick={() => {
                setStep("phone");
                setOtp("");
                setError(null);
              }}
              sx={{ mt: 1, color: "text.secondary", textTransform: "none" }}
            >
              Change number
            </Button>
          </>
        )}

        {error && (
          <Typography sx={{ color: "error.main", fontSize: 12, mt: 2, textAlign: "center" }}>
            {error}
          </Typography>
        )}
      </Box>
    </Box>
  );
}
