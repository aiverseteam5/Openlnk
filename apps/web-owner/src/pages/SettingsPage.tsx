/**
 * Settings page — quiet hours and smart reminder preferences.
 *
 * DESIGN.md: DM Sans + JetBrains Mono, no avatars, no dark mode.
 * Commitment lifecycle stage: protect (smart reminders).
 */

import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchLearningProfile, updateQuietHours } from "../api/client";
import { useAppStore } from "../store/app";
import { fonts } from "@openlnk/ui";

function formatHour(hour: number): string {
  const h = hour % 24;
  const suffix = h >= 12 ? "PM" : "AM";
  const display = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${display}:00 ${suffix}`;
}

export default function SettingsPage() {
  const { principalId } = useAppStore();
  const queryClient = useQueryClient();

  const { data: profile, isLoading } = useQuery({
    queryKey: ["learning-profile", principalId],
    queryFn: () => fetchLearningProfile(principalId),
  });

  const [qhStart, setQhStart] = useState("");
  const [qhEnd, setQhEnd] = useState("");

  // Populate form from server data
  const startValue = qhStart || profile?.quiet_hours_start || "";
  const endValue = qhEnd || profile?.quiet_hours_end || "";

  const mutation = useMutation({
    mutationFn: () => updateQuietHours(principalId, startValue, endValue),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["learning-profile"] });
      setQhStart("");
      setQhEnd("");
    },
  });

  return (
    <Box sx={{ maxWidth: 600, mx: "auto" }}>
      <Typography variant="h6" sx={{ mb: 0.5 }}>
        Settings
      </Typography>
      <Typography
        sx={{
          fontFamily: fonts.mono,
          fontSize: 11,
          color: "text.secondary",
          mb: 3,
        }}
      >
        REMINDERS & QUIET HOURS
      </Typography>

      {isLoading && (
        <Typography sx={{ color: "text.secondary" }}>
          {"\u2014"} Loading...
        </Typography>
      )}

      {profile && (
        <>
          {/* Smart Nudge Suggestion */}
          <Box
            sx={{
              border: "1px solid #E8E4DD",
              p: 2,
              mb: 3,
              backgroundColor: "#FAFAF8",
            }}
          >
            <Typography
              sx={{
                fontFamily: fonts.mono,
                fontSize: 10,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "#6B6456",
                mb: 1,
              }}
            >
              SMART NUDGE TIMING
            </Typography>
            {profile.preferred_nudge_hour !== null ? (
              <Box>
                <Typography sx={{ fontSize: 14, mb: 0.5 }}>
                  Based on {profile.data_points} commitment events, your preferred
                  response time is around{" "}
                  <Typography
                    component="span"
                    sx={{ fontFamily: fonts.mono, fontWeight: 600 }}
                  >
                    {formatHour(profile.preferred_nudge_hour)}
                  </Typography>
                  .
                </Typography>
                <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                  Reminders will be timed to match your activity pattern.
                </Typography>
              </Box>
            ) : (
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                Not enough data yet ({profile.data_points}/5 signals).
                Continue using the app to build your nudge profile.
              </Typography>
            )}

            {profile.suggested_quiet_hours && (
              <Box sx={{ mt: 2, pt: 1.5, borderTop: "1px solid #E8E4DD" }}>
                <Typography sx={{ fontSize: 13 }}>
                  Suggested quiet hours:{" "}
                  <Typography
                    component="span"
                    sx={{ fontFamily: fonts.mono, fontWeight: 600 }}
                  >
                    {formatHour(profile.suggested_quiet_hours.start_hour)}
                    {" \u2013 "}
                    {formatHour(profile.suggested_quiet_hours.end_hour)}
                  </Typography>
                </Typography>
              </Box>
            )}
          </Box>

          {/* Quiet Hours Config */}
          <Box
            sx={{
              border: "1px solid #E8E4DD",
              p: 2,
              mb: 3,
              backgroundColor: "#FAFAF8",
            }}
          >
            <Typography
              sx={{
                fontFamily: fonts.mono,
                fontSize: 10,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "#6B6456",
                mb: 1.5,
              }}
            >
              QUIET HOURS
            </Typography>
            <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
              No reminders will be sent during quiet hours. Actions queued
              during this window will send when it ends.
            </Typography>
            <Box sx={{ display: "flex", gap: 2, alignItems: "center", mb: 2 }}>
              <TextField
                label="Start"
                type="time"
                size="small"
                value={startValue}
                onChange={(e) => setQhStart(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
                sx={{ width: 140 }}
              />
              <Typography sx={{ color: "text.secondary" }}>{"\u2013"}</Typography>
              <TextField
                label="End"
                type="time"
                size="small"
                value={endValue}
                onChange={(e) => setQhEnd(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
                sx={{ width: 140 }}
              />
            </Box>
            <Button
              variant="contained"
              size="small"
              onClick={() => mutation.mutate()}
              disabled={!startValue || !endValue || mutation.isPending}
              sx={{
                textTransform: "none",
                fontFamily: fonts.mono,
                fontSize: 12,
                letterSpacing: "0.04em",
              }}
            >
              {mutation.isPending ? "Saving..." : "Save Quiet Hours"}
            </Button>
            {mutation.isSuccess && (
              <Typography
                sx={{
                  fontFamily: fonts.mono,
                  fontSize: 11,
                  color: "#2E7D32",
                  mt: 1,
                }}
              >
                SAVED
              </Typography>
            )}
          </Box>
        </>
      )}
    </Box>
  );
}
