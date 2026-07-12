/**
 * AI Extract page — paste text or upload image for commitment extraction.
 *
 * Three input modes:
 * 1. Paste text (WhatsApp messages, conversations)
 * 2. Upload image (circulars, fee notices, receipts)
 * 3. Record voice (browser microphone) — future enhancement
 *
 * All routes → POST /v1/extract → commitments created in proposed state.
 * DESIGN.md: DM Sans + JetBrains Mono, #F5F2EC bg, no shadows.
 */

import { useState, useRef } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fonts } from "@openlnk/ui";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

type Mode = "text" | "image";

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("openlnk_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function ExtractPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const extractMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        provenance_kind: mode === "image" ? "camera" : "message",
      };

      if (mode === "text") {
        if (!text.trim()) throw new Error("Enter some text to extract from");
        body.text = text;
      } else if (mode === "image") {
        if (!imageBase64) throw new Error("Upload an image first");
        body.image_base64 = imageBase64;
      }

      const res = await fetch(`${API_BASE}/extract`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": self.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          ...getAuthHeaders(),
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Extraction failed (${res.status})`);
      }
      return res.json();
    },
    onSuccess: () => {
      setResult("Commitments extracted! Check your Inbox to review.");
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
      setText("");
      setImagePreview(null);
      setImageBase64(null);
    },
  });

  const handleImageUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setImagePreview(dataUrl);
      // Strip data:image/...;base64, prefix
      setImageBase64(dataUrl.split(",")[1]);
    };
    reader.readAsDataURL(file);
  };

  return (
    <Box sx={{ maxWidth: 720, mx: "auto" }}>
      <Typography variant="h6" sx={{ mb: 0.5 }}>
        AI Extract
      </Typography>
      <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 3 }}>
        Paste a message or upload a document — AI will extract commitments automatically
      </Typography>

      {/* Mode tabs */}
      <Box sx={{ display: "flex", gap: 0, mb: 2 }}>
        {(["text", "image"] as Mode[]).map((m) => (
          <Box
            key={m}
            onClick={() => {
              setMode(m);
              setResult(null);
            }}
            sx={{
              px: 2,
              py: 0.75,
              cursor: "pointer",
              fontFamily: fonts.mono,
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.08em",
              borderBottom: "2px solid",
              borderColor: mode === m ? "primary.main" : "transparent",
              color: mode === m ? "primary.main" : "text.secondary",
              "&:hover": { color: "primary.main" },
            }}
          >
            {m === "text" ? "PASTE TEXT" : "UPLOAD IMAGE"}
          </Box>
        ))}
      </Box>

      {/* Text input */}
      {mode === "text" && (
        <Box>
          <TextField
            fullWidth
            multiline
            minRows={6}
            maxRows={12}
            placeholder={"Paste a WhatsApp message, conversation, or any text containing commitments...\n\nExample:\n\"Arjun's July fee is Rs 5000, due by 15th. Please send by UPI.\nAlso, PTM is on August 5th at 4pm.\""}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setResult(null);
            }}
            sx={{
              mb: 2,
              "& .MuiInputBase-input": { fontSize: 14, lineHeight: 1.6 },
            }}
          />
          <Button
            variant="contained"
            fullWidth
            disabled={extractMutation.isPending || !text.trim()}
            onClick={() => extractMutation.mutate()}
          >
            {extractMutation.isPending ? "Extracting..." : "Extract Commitments"}
          </Button>
        </Box>
      )}

      {/* Image upload */}
      {mode === "image" && (
        <Box>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleImageUpload(f);
            }}
          />

          {!imagePreview ? (
            <Box
              onClick={() => fileRef.current?.click()}
              sx={{
                border: "2px dashed",
                borderColor: "divider",
                borderRadius: "2px",
                py: 6,
                textAlign: "center",
                cursor: "pointer",
                "&:hover": { borderColor: "primary.main", bgcolor: "#FAFAF8" },
                mb: 2,
              }}
            >
              <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
                Click to upload a circular, fee notice, receipt, or schedule
              </Typography>
              <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.5 }}>
                JPG, PNG, or PDF
              </Typography>
            </Box>
          ) : (
            <Box sx={{ mb: 2 }}>
              <Box
                component="img"
                src={imagePreview}
                sx={{
                  width: "100%",
                  maxHeight: 300,
                  objectFit: "contain",
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: "2px",
                  mb: 1,
                }}
              />
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  variant="contained"
                  fullWidth
                  disabled={extractMutation.isPending}
                  onClick={() => extractMutation.mutate()}
                >
                  {extractMutation.isPending ? "Extracting..." : "Extract from Image"}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => {
                    setImagePreview(null);
                    setImageBase64(null);
                  }}
                >
                  Clear
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      )}

      {/* Success message */}
      {result && (
        <Box
          sx={{
            mt: 2,
            p: 2,
            bgcolor: "#F0FFF4",
            border: "1px solid #C6F6D5",
            borderRadius: "2px",
          }}
        >
          <Typography sx={{ fontSize: 13, mb: 1 }}>{result}</Typography>
          <Button
            variant="outlined"
            size="small"
            onClick={() => navigate("/inbox")}
          >
            Go to Inbox
          </Button>
        </Box>
      )}

      {/* Error */}
      {extractMutation.isError && (
        <Typography sx={{ color: "error.main", fontSize: 12, mt: 2 }}>
          {extractMutation.error instanceof Error
            ? extractMutation.error.message
            : "Extraction failed"}
        </Typography>
      )}
    </Box>
  );
}
