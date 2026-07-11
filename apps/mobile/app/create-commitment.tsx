/**
 * Create commitment screen — manual entry.
 *
 * Class-specific validation: fee/payment require amount (OL-009).
 * POST /commitments with Idempotency-Key.
 * Lifecycle stage: create.
 */

import { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TextInput,
  Pressable,
} from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useMutation, useQueryClient } from "@tanstack/react-query";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

const CLASSES = ["fee", "schedule", "task", "payment", "custom"] as const;

export default function CreateCommitmentScreen() {
  const queryClient = useQueryClient();

  const [title, setTitle] = useState("");
  const [commitmentClass, setCommitmentClass] = useState<string>("task");
  const [amount, setAmount] = useState("");
  const [dueAt, setDueAt] = useState("");

  const requiresAmount = commitmentClass === "fee" || commitmentClass === "payment";

  const createMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        title,
        class: commitmentClass,
        currency: "INR",
        owner_id: "00000000-0000-0000-0000-000000000001",
        context_id: "00000000-0000-0000-0000-000000000001",
      };
      if (amount) body.amount_paise = Math.round(parseFloat(amount) * 100);
      if (dueAt) body.due_at = new Date(dueAt).toISOString();

      const res = await fetch(`${API_BASE}/v1/commitments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
      router.back();
    },
  });

  const valid =
    title.trim().length > 0 &&
    (!requiresAmount || (amount !== "" && parseFloat(amount) > 0));

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
            lineHeight: 22,
            color: "#1A1814",
          }}
        >
          Create Commitment
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <View
          className="border border-border bg-surface p-lg"
          style={{ borderRadius: 2 }}
        >
          {/* Title */}
          <Text
            className="text-text-muted mb-xs"
            style={{ fontFamily: "DM Sans", fontSize: 12 }}
          >
            Title *
          </Text>
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="e.g. Monthly tuition fee"
            maxLength={500}
            className="border border-border bg-surface px-md py-sm mb-lg"
            style={{
              fontFamily: "DM Sans",
              fontSize: 14,
              borderRadius: 2,
              color: "#1A1814",
            }}
          />

          {/* Class */}
          <Text
            className="text-text-muted mb-xs"
            style={{ fontFamily: "DM Sans", fontSize: 12 }}
          >
            Class
          </Text>
          <View className="flex-row flex-wrap gap-sm mb-lg">
            {CLASSES.map((c) => (
              <Pressable
                key={c}
                onPress={() => setCommitmentClass(c)}
                style={{
                  backgroundColor: commitmentClass === c ? "#1A4FBF" : "#F3F4F6",
                  borderRadius: 9999,
                  paddingHorizontal: 12,
                  paddingVertical: 4,
                }}
              >
                <Text
                  style={{
                    fontFamily: "JetBrains Mono SemiBold",
                    fontSize: 11,
                    letterSpacing: 1.1,
                    color: commitmentClass === c ? "#FFFFFF" : "#374151",
                    textTransform: "uppercase",
                  }}
                >
                  {c}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Amount */}
          <Text
            className="text-text-muted mb-xs"
            style={{ fontFamily: "DM Sans", fontSize: 12 }}
          >
            Amount (INR){requiresAmount ? " *" : ""}
          </Text>
          <TextInput
            value={amount}
            onChangeText={setAmount}
            placeholder="0.00"
            keyboardType="numeric"
            className="border border-border bg-surface px-md py-sm mb-lg"
            style={{
              fontFamily: "JetBrains Mono",
              fontSize: 14,
              borderRadius: 2,
              color: "#1A1814",
            }}
          />
          {requiresAmount && !amount && (
            <Text
              className="-mt-md mb-lg"
              style={{ fontFamily: "DM Sans", fontSize: 11, color: "#92600A" }}
            >
              Required for {commitmentClass} commitments
            </Text>
          )}

          {/* Due date (text input — no date picker in basic scaffold) */}
          <Text
            className="text-text-muted mb-xs"
            style={{ fontFamily: "DM Sans", fontSize: 12 }}
          >
            Due date (YYYY-MM-DD)
          </Text>
          <TextInput
            value={dueAt}
            onChangeText={setDueAt}
            placeholder="2026-08-15"
            className="border border-border bg-surface px-md py-sm mb-lg"
            style={{
              fontFamily: "JetBrains Mono",
              fontSize: 14,
              borderRadius: 2,
              color: "#1A1814",
            }}
          />

          {/* Submit */}
          <Pressable
            disabled={!valid || createMutation.isPending}
            onPress={() => createMutation.mutate()}
            style={{
              backgroundColor: valid ? "#1A4FBF" : "#AAA49A",
              borderRadius: 4,
              paddingVertical: 12,
              alignItems: "center",
            }}
          >
            <Text style={{ fontFamily: "DM Sans Medium", fontSize: 14, color: "#FFFFFF" }}>
              {createMutation.isPending ? "Creating..." : "Create"}
            </Text>
          </Pressable>

          {createMutation.isError && (
            <Text
              className="mt-sm"
              style={{ fontFamily: "DM Sans", fontSize: 12, color: "#B91C1C" }}
            >
              Failed to create commitment.
            </Text>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
