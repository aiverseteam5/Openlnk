/**
 * Camera capture screen — photograph documents for extraction (OL-022).
 *
 * Captures receipts, circulars, notices. Sent to extraction pipeline as base64.
 * Content is ephemeral — never persisted server-side (ADR-002, OL-024).
 * DESIGN.md: no skeleton loaders, dashes for loading state.
 */

import { useState, useRef } from "react";
import { View, Text, Pressable, Image } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as FileSystem from "expo-file-system";
import { useAppStore } from "@/store/app";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

type CaptureState = "preview" | "captured" | "sending" | "done" | "error";

export default function CaptureCameraScreen() {
  const { principalId, selectedContextId } = useAppStore();
  const [permission, requestPermission] = useCameraPermissions();
  const [state, setState] = useState<CaptureState>("preview");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const cameraRef = useRef<CameraView>(null);

  async function takePhoto() {
    if (!cameraRef.current) return;
    const photo = await cameraRef.current.takePictureAsync({ quality: 0.8 });
    if (photo) {
      setPhotoUri(photo.uri);
      setState("captured");
    }
  }

  async function sendForExtraction() {
    if (!photoUri) return;
    setState("sending");

    const base64 = await FileSystem.readAsStringAsync(photoUri, {
      encoding: FileSystem.EncodingType.Base64,
    });

    // Clean up local file
    await FileSystem.deleteAsync(photoUri, { idempotent: true });

    const res = await fetch(`${API_BASE}/v1/extract`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Principal-Id": principalId,
        "Idempotency-Key": `camera-${Date.now()}`,
      },
      body: JSON.stringify({
        message_id: crypto.randomUUID(),
        thread_id: selectedContextId ?? principalId,
        provenance_kind: "camera",
        image_base64: base64,
      }),
    });

    if (res.ok) {
      setState("done");
      setTimeout(() => router.back(), 1500);
    } else {
      setState("error");
    }
  }

  function retake() {
    setPhotoUri(null);
    setState("preview");
  }

  if (!permission) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center">
        <Text className="text-text-muted" style={{ fontFamily: "DM Sans", fontSize: 14 }}>
          {"\u2014"}
        </Text>
      </SafeAreaView>
    );
  }

  if (!permission.granted) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center px-4">
        <Text
          className="text-text-muted mb-md"
          style={{ fontFamily: "DM Sans", fontSize: 14, textAlign: "center" }}
        >
          Camera permission is required to capture documents.
        </Text>
        <Pressable
          onPress={requestPermission}
          style={{
            backgroundColor: "#1A4FBF",
            borderRadius: 4,
            paddingHorizontal: 16,
            paddingVertical: 10,
          }}
        >
          <Text style={{ fontFamily: "DM Sans Medium", fontSize: 14, color: "#FFFFFF" }}>
            Grant Permission
          </Text>
        </Pressable>
        <Pressable onPress={() => router.back()} className="mt-md">
          <Text className="text-text-muted" style={{ fontFamily: "DM Sans", fontSize: 14 }}>
            Cancel
          </Text>
        </Pressable>
      </SafeAreaView>
    );
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
          Document Capture
        </Text>
      </View>

      {state === "preview" && (
        <View className="flex-1">
          <CameraView
            ref={cameraRef}
            style={{ flex: 1 }}
            facing="back"
          />
          <View className="absolute bottom-0 left-0 right-0 items-center pb-8">
            <Pressable
              onPress={takePhoto}
              style={{
                width: 72,
                height: 72,
                borderRadius: 36,
                backgroundColor: "#FFFFFF",
                borderWidth: 4,
                borderColor: "#1A4FBF",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <View
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 28,
                  backgroundColor: "#1A4FBF",
                }}
              />
            </Pressable>
          </View>
        </View>
      )}

      {state === "captured" && photoUri && (
        <View className="flex-1">
          <Image
            source={{ uri: photoUri }}
            style={{ flex: 1 }}
            resizeMode="contain"
          />
          <View className="flex-row gap-sm justify-center py-md px-4">
            <Pressable
              onPress={retake}
              style={{
                flex: 1,
                borderWidth: 1,
                borderColor: "#D6D0C4",
                borderRadius: 4,
                paddingVertical: 12,
                alignItems: "center",
              }}
            >
              <Text style={{ fontFamily: "DM Sans Medium", fontSize: 14, color: "#1A1814" }}>
                Retake
              </Text>
            </Pressable>
            <Pressable
              onPress={sendForExtraction}
              style={{
                flex: 1,
                backgroundColor: "#1A4FBF",
                borderRadius: 4,
                paddingVertical: 12,
                alignItems: "center",
              }}
            >
              <Text style={{ fontFamily: "DM Sans Medium", fontSize: 14, color: "#FFFFFF" }}>
                Extract
              </Text>
            </Pressable>
          </View>
        </View>
      )}

      {(state === "sending" || state === "done" || state === "error") && (
        <View className="flex-1 items-center justify-center">
          <Text
            className="text-text-muted"
            style={{ fontFamily: "DM Sans Medium", fontSize: 14 }}
          >
            {state === "sending" && "\u2014 Sending for extraction..."}
            {state === "done" && "Extraction queued. Returning..."}
            {state === "error" && "Extraction failed. Try again."}
          </Text>
        </View>
      )}
    </SafeAreaView>
  );
}
