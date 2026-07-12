/**
 * Voice capture screen — record and send to extraction pipeline (OL-021).
 *
 * Uses expo-av for recording. Audio sent to extraction API as base64.
 * Content is ephemeral — never persisted server-side (ADR-002, OL-024).
 * DESIGN.md: no skeleton loaders, dashes for loading state.
 */

import { useState, useRef } from "react";
import { View, Text, Pressable } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Audio } from "expo-av";
import * as FileSystem from "expo-file-system";
import { useAppStore } from "@/store/app";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

type RecordingState = "idle" | "recording" | "sending" | "done" | "error";

export default function CaptureVoiceScreen() {
  const { principalId, selectedContextId } = useAppStore();
  const [state, setState] = useState<RecordingState>("idle");
  const [duration, setDuration] = useState(0);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function startRecording() {
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) {
      setState("error");
      return;
    }

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    const recording = new Audio.Recording();
    await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
    await recording.startAsync();

    recordingRef.current = recording;
    setState("recording");
    setDuration(0);

    intervalRef.current = setInterval(() => {
      setDuration((d) => d + 1);
    }, 1000);
  }

  async function stopAndSend() {
    if (intervalRef.current) clearInterval(intervalRef.current);

    const recording = recordingRef.current;
    if (!recording) return;

    setState("sending");
    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    if (!uri) {
      setState("error");
      return;
    }

    // Read as base64 for ephemeral extraction (OL-024: not persisted server-side)
    const base64 = await FileSystem.readAsStringAsync(uri, {
      encoding: FileSystem.EncodingType.Base64,
    });

    // Clean up local file
    await FileSystem.deleteAsync(uri, { idempotent: true });

    // Send to extraction API
    const res = await fetch(`${API_BASE}/v1/extract`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Principal-Id": principalId,
        "Idempotency-Key": `voice-${Date.now()}`,
      },
      body: JSON.stringify({
        message_id: crypto.randomUUID(),
        thread_id: selectedContextId ?? principalId,
        provenance_kind: "voice",
        audio_base64: base64,
      }),
    });

    if (res.ok) {
      setState("done");
      setTimeout(() => router.back(), 1500);
    } else {
      setState("error");
    }
  }

  function formatDuration(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  }

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={["top"]}>
      {/* Header */}
      <View className="px-4 py-3 border-b border-border flex-row items-center">
        <Pressable onPress={() => router.back()}>
          <Text
            className="text-text-muted mr-3"
            style={{ fontFamily: "DM Sans", fontSize: 14 }}
          >
            &larr; Back
          </Text>
        </Pressable>
        <Text
          style={{
            fontFamily: "DM Sans SemiBold",
            fontSize: 16,
            color: "#1A1814",
          }}
        >
          Voice Capture
        </Text>
      </View>

      <View className="flex-1 items-center justify-center px-4">
        {/* Duration display */}
        <Text
          style={{
            fontFamily: "JetBrains Mono SemiBold",
            fontSize: 48,
            color: state === "recording" ? "#B91C1C" : "#1A1814",
            marginBottom: 32,
          }}
        >
          {state === "recording" ? formatDuration(duration) : "\u2014"}
        </Text>

        {/* Status */}
        <Text
          className="text-text-muted mb-lg"
          style={{ fontFamily: "DM Sans", fontSize: 14, textAlign: "center" }}
        >
          {state === "idle" && "Tap to start recording a voice note"}
          {state === "recording" && "Recording... tap again to stop and extract"}
          {state === "sending" && "\u2014 Sending for extraction..."}
          {state === "done" && "Extraction queued. Returning..."}
          {state === "error" && "Failed. Check microphone permissions."}
        </Text>

        {/* Record button */}
        {(state === "idle" || state === "recording") && (
          <Pressable
            onPress={state === "idle" ? startRecording : stopAndSend}
            style={{
              width: 80,
              height: 80,
              borderRadius: 40,
              backgroundColor: state === "recording" ? "#B91C1C" : "#1A4FBF",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Text
              style={{
                fontFamily: "JetBrains Mono SemiBold",
                fontSize: 13,
                color: "#FFFFFF",
              }}
            >
              {state === "idle" ? "REC" : "STOP"}
            </Text>
          </Pressable>
        )}
      </View>
    </SafeAreaView>
  );
}
