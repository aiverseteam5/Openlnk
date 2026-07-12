/**
 * Login screen — phone OTP authentication (OL-146).
 *
 * Step 1: Phone input (E.164, India-first)
 * Step 2: 6-digit OTP verification
 * On success: store tokens in SecureStore, redirect to home.
 *
 * DESIGN.md: DM Sans + JetBrains Mono, #F5F2EC bg, #1A4FBF accent.
 */

import { useState } from "react";
import { View, Text, TextInput, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppStore } from "@/store/app";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

type Step = "phone" | "otp";

export default function LoginScreen() {
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
      const res = await fetch(`${API_BASE}/v1/auth/send-otp`, {
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
      const res = await fetch(`${API_BASE}/v1/auth/verify-otp`, {
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
    <SafeAreaView style={{ flex: 1, backgroundColor: "#F5F2EC" }}>
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          paddingHorizontal: 32,
        }}
      >
        <View
          style={{
            width: "100%",
            maxWidth: 360,
            backgroundColor: "#FFFFFF",
            borderWidth: 1,
            borderColor: "#D6D0C4",
            borderRadius: 2,
            padding: 24,
          }}
        >
          {/* Logo */}
          <Text
            style={{
              fontFamily: "JetBrains Mono SemiBold",
              fontSize: 15,
              letterSpacing: 1.2,
              color: "#1A4FBF",
              textAlign: "center",
              marginBottom: 24,
            }}
          >
            OPENLNK
          </Text>

          {step === "phone" && (
            <>
              <Text
                style={{
                  fontFamily: "DM Sans",
                  fontSize: 14,
                  color: "#6B7280",
                  marginBottom: 16,
                }}
              >
                Enter your phone number to sign in
              </Text>
              <TextInput
                value={phone}
                onChangeText={setPhone}
                placeholder="+919876543210"
                keyboardType="phone-pad"
                autoFocus
                style={{
                  fontFamily: "JetBrains Mono",
                  fontSize: 16,
                  borderWidth: 1,
                  borderColor: "#D6D0C4",
                  borderRadius: 2,
                  paddingHorizontal: 12,
                  paddingVertical: 10,
                  marginBottom: 16,
                  color: "#1A1814",
                }}
              />
              <Pressable
                onPress={handleSendOtp}
                disabled={loading || phone.length < 10}
                style={{
                  backgroundColor: loading || phone.length < 10 ? "#9CA3AF" : "#1A4FBF",
                  borderRadius: 4,
                  paddingVertical: 12,
                  alignItems: "center",
                }}
              >
                {loading ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <Text
                    style={{
                      fontFamily: "DM Sans SemiBold",
                      fontSize: 14,
                      color: "#FFFFFF",
                    }}
                  >
                    Send OTP
                  </Text>
                )}
              </Pressable>
            </>
          )}

          {step === "otp" && (
            <>
              <Text
                style={{
                  fontFamily: "DM Sans",
                  fontSize: 14,
                  color: "#6B7280",
                  marginBottom: 4,
                }}
              >
                Enter the 6-digit code sent to
              </Text>
              <Text
                style={{
                  fontFamily: "JetBrains Mono",
                  fontSize: 13,
                  color: "#1A1814",
                  marginBottom: 16,
                }}
              >
                {phone}
              </Text>
              <TextInput
                value={otp}
                onChangeText={(t) => setOtp(t.replace(/\D/g, "").slice(0, 6))}
                placeholder="123456"
                keyboardType="number-pad"
                maxLength={6}
                autoFocus
                style={{
                  fontFamily: "JetBrains Mono SemiBold",
                  fontSize: 24,
                  letterSpacing: 8,
                  textAlign: "center",
                  borderWidth: 1,
                  borderColor: "#D6D0C4",
                  borderRadius: 2,
                  paddingHorizontal: 12,
                  paddingVertical: 12,
                  marginBottom: 16,
                  color: "#1A1814",
                }}
              />
              <Pressable
                onPress={handleVerifyOtp}
                disabled={loading || otp.length !== 6}
                style={{
                  backgroundColor: loading || otp.length !== 6 ? "#9CA3AF" : "#1A4FBF",
                  borderRadius: 4,
                  paddingVertical: 12,
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                {loading ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <Text
                    style={{
                      fontFamily: "DM Sans SemiBold",
                      fontSize: 14,
                      color: "#FFFFFF",
                    }}
                  >
                    Verify
                  </Text>
                )}
              </Pressable>
              <Pressable
                onPress={() => {
                  setStep("phone");
                  setOtp("");
                  setError(null);
                }}
              >
                <Text
                  style={{
                    fontFamily: "DM Sans",
                    fontSize: 13,
                    color: "#6B7280",
                    textAlign: "center",
                  }}
                >
                  Change number
                </Text>
              </Pressable>
            </>
          )}

          {error && (
            <Text
              style={{
                fontFamily: "DM Sans",
                fontSize: 12,
                color: "#C62828",
                textAlign: "center",
                marginTop: 12,
              }}
            >
              {error}
            </Text>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}
