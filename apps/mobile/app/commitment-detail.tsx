/**
 * Commitment detail screen — full data, state transitions, corrections.
 *
 * DESIGN.md: State changes are timestamped audit entries, not toasts.
 * Corrections in ≤2 taps (OL-026).
 * No shadows, no skeleton loaders (dashes).
 */

import { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  TextInput,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchCommitment,
  transitionState,
} from "@/api/client";
import { useAppStore } from "@/store/app";
import { stateColors, type CommitmentState } from "@openlnk/ui";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

const TRANSITIONS: Record<string, { label: string; target: string }[]> = {
  proposed: [
    { label: "Accept", target: "accepted" },
    { label: "Reject", target: "cancelled" },
  ],
  accepted: [{ label: "Mark In Progress", target: "in_progress" }],
  in_progress: [
    { label: "Mark Done", target: "done" },
    { label: "Mark Broken", target: "broken" },
  ],
};

function formatAmount(paise: number | null, currency: string): string {
  if (paise === null) return "\u2014";
  const amt = paise / 100;
  if (currency === "INR") return `\u20B9${amt.toLocaleString("en-IN")}`;
  return `${currency} ${amt.toFixed(2)}`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DataRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <View className="flex-row justify-between py-[6px]">
      <Text
        className="text-text-muted"
        style={{ fontFamily: "DM Sans", fontSize: 12 }}
      >
        {label}
      </Text>
      <Text
        style={{
          fontFamily: mono ? "JetBrains Mono SemiBold" : "DM Sans SemiBold",
          fontSize: 14,
          color: "#1A1814",
        }}
      >
        {value}
      </Text>
    </View>
  );
}

export default function CommitmentDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { principalId } = useAppStore();
  const queryClient = useQueryClient();

  const [correctionMode, setCorrectionMode] = useState<"edit" | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAmount, setEditAmount] = useState("");

  const { data: commitment, isLoading } = useQuery({
    queryKey: ["commitment", id],
    queryFn: () => fetchCommitment(principalId, id!),
    enabled: !!id,
  });

  const transitionMutation = useMutation({
    mutationFn: ({ target, version }: { target: string; version: number }) =>
      transitionState(principalId, id!, target, version),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitment", id] });
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  const correctMutation = useMutation({
    mutationFn: async (body: { action: string; edits?: Record<string, unknown> }) => {
      const res = await fetch(`${API_BASE}/v1/commitments/${id}/correct`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Principal-Id": principalId,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      setCorrectionMode(null);
      void queryClient.invalidateQueries({ queryKey: ["commitment", id] });
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  if (isLoading || !commitment) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center">
        <Text
          className="text-text-muted"
          style={{ fontFamily: "DM Sans Medium", fontSize: 14 }}
        >
          {"\u2014"} Loading...
        </Text>
      </SafeAreaView>
    );
  }

  const stateKey: CommitmentState = commitment.at_risk
    ? "overdue"
    : (commitment.state as CommitmentState);
  const sc = stateColors[stateKey] ?? stateColors.proposed;
  const transitions = TRANSITIONS[commitment.state] ?? [];

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
          className="text-accent tracking-[0.08em]"
          style={{ fontFamily: "JetBrains Mono SemiBold", fontSize: 13 }}
        >
          OPENLNK
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        {/* Detail card */}
        <View
          className="border border-border bg-surface overflow-hidden mb-sm flex-row"
          style={{ borderRadius: 2 }}
        >
          <View style={{ width: 3, backgroundColor: sc.leftBar }} />
          <View className="flex-1 px-lg py-md">
            {/* ID + Badge */}
            <View className="flex-row justify-between items-center mb-sm">
              <Text
                className="text-text-muted"
                style={{ fontFamily: "JetBrains Mono", fontSize: 11 }}
              >
                CMT-{commitment.id.slice(0, 4).toUpperCase()}
              </Text>
              <View
                style={{
                  backgroundColor: sc.background,
                  borderRadius: 9999,
                  paddingHorizontal: 8,
                  paddingVertical: 2,
                }}
              >
                <Text
                  style={{
                    fontFamily: "JetBrains Mono SemiBold",
                    fontSize: 11,
                    color: sc.text,
                    letterSpacing: 1.1,
                  }}
                >
                  {sc.label}
                </Text>
              </View>
            </View>

            {/* Title */}
            <Text
              className="mb-md"
              style={{
                fontFamily: "DM Sans SemiBold",
                fontSize: 18,
                lineHeight: 24,
                color: "#1A1814",
              }}
            >
              {commitment.title}
            </Text>

            {/* Data rows */}
            <DataRow label="Class" value={commitment.class} />
            <DataRow
              label="Amount"
              value={formatAmount(commitment.amount_paise, commitment.currency)}
              mono
            />
            <DataRow label="Due" value={formatDate(commitment.due_at)} mono />
            <DataRow label="Created" value={formatDate(commitment.created_at)} mono />
            <DataRow label="Version" value={String(commitment.version)} mono />
          </View>
        </View>

        {/* State transition buttons */}
        {transitions.length > 0 && (
          <View className="flex-row gap-sm mb-md">
            {transitions.map((t) => (
              <Pressable
                key={t.target}
                className="flex-1 py-[10px] items-center"
                style={{
                  backgroundColor:
                    t.target === "cancelled" || t.target === "broken"
                      ? "transparent"
                      : "#1A4FBF",
                  borderRadius: 4,
                  borderWidth: t.target === "cancelled" || t.target === "broken" ? 1 : 0,
                  borderColor: "#D6D0C4",
                }}
                disabled={transitionMutation.isPending}
                onPress={() =>
                  transitionMutation.mutate({
                    target: t.target,
                    version: commitment.version,
                  })
                }
              >
                <Text
                  style={{
                    fontFamily: "DM Sans Medium",
                    fontSize: 14,
                    color:
                      t.target === "cancelled" || t.target === "broken"
                        ? "#1A1814"
                        : "#FFFFFF",
                  }}
                >
                  {t.label}
                </Text>
              </Pressable>
            ))}
          </View>
        )}

        {transitionMutation.isError && (
          <Text
            className="mb-sm"
            style={{ fontFamily: "DM Sans", fontSize: 12, color: "#B91C1C" }}
          >
            Transition failed. The commitment may have been updated.
          </Text>
        )}

        {/* UPI payment button (OL-010, OL-103) */}
        {commitment.state === "accepted" &&
          (commitment.class === "fee" || commitment.class === "payment") &&
          commitment.amount_paise !== null && (
            <Pressable
              onPress={() => {
                const url = `upi://pay?am=${commitment.amount_paise! / 100}&cu=${commitment.currency}&tn=${encodeURIComponent(commitment.title)}`;
                import("expo-linking").then((Linking) => Linking.openURL(url));
              }}
              style={{
                backgroundColor: "#1A4FBF",
                borderRadius: 4,
                paddingVertical: 12,
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <Text
                style={{
                  fontFamily: "JetBrains Mono SemiBold",
                  fontSize: 14,
                  color: "#FFFFFF",
                }}
              >
                Pay {formatAmount(commitment.amount_paise, commitment.currency)} via UPI
              </Text>
            </Pressable>
          )}

        {/* WhatsApp share CTA (OL-103a) — only when state is done */}
        {commitment.state === "done" && (
          <Pressable
            onPress={() => {
              const msg = `${commitment.title} — confirmed on ${formatDate(commitment.created_at)}`;
              const url = `https://wa.me/?text=${encodeURIComponent(msg)}`;
              import("expo-linking").then((Linking) => Linking.openURL(url));
            }}
            style={{
              borderWidth: 1,
              borderColor: "#1A4FBF",
              borderRadius: 4,
              paddingVertical: 12,
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <Text
              style={{
                fontFamily: "DM Sans Medium",
                fontSize: 14,
                color: "#1A4FBF",
              }}
            >
              Share confirmation to WhatsApp
            </Text>
          </Pressable>
        )}

        {/* Corrections — ≤2 taps (OL-026) */}
        {commitment.state === "proposed" && (
          <View className="border-t border-border pt-md">
            <Text
              className="text-text-muted mb-sm"
              style={{
                fontFamily: "DM Sans SemiBold",
                fontSize: 11,
                letterSpacing: 0.88,
              }}
            >
              EXTRACTION CORRECTION
            </Text>

            {correctionMode === null ? (
              <View className="flex-row gap-sm">
                <Pressable
                  className="flex-1 py-[10px] items-center border border-border"
                  style={{ borderRadius: 4 }}
                  disabled={correctMutation.isPending}
                  onPress={() => correctMutation.mutate({ action: "reject" })}
                >
                  <Text
                    style={{
                      fontFamily: "DM Sans Medium",
                      fontSize: 14,
                      color: "#B91C1C",
                    }}
                  >
                    Reject
                  </Text>
                </Pressable>
                <Pressable
                  className="flex-1 py-[10px] items-center border border-border"
                  style={{ borderRadius: 4 }}
                  onPress={() => {
                    setEditTitle(commitment.title);
                    setEditAmount(
                      commitment.amount_paise !== null
                        ? String(commitment.amount_paise / 100)
                        : "",
                    );
                    setCorrectionMode("edit");
                  }}
                >
                  <Text
                    style={{
                      fontFamily: "DM Sans Medium",
                      fontSize: 14,
                      color: "#1A4FBF",
                    }}
                  >
                    Edit &amp; correct
                  </Text>
                </Pressable>
              </View>
            ) : (
              <View>
                <TextInput
                  value={editTitle}
                  onChangeText={setEditTitle}
                  placeholder="Title"
                  className="border border-border bg-surface px-md py-sm mb-sm"
                  style={{
                    fontFamily: "DM Sans",
                    fontSize: 14,
                    borderRadius: 2,
                    color: "#1A1814",
                  }}
                />
                <TextInput
                  value={editAmount}
                  onChangeText={setEditAmount}
                  placeholder="Amount"
                  keyboardType="numeric"
                  className="border border-border bg-surface px-md py-sm mb-sm"
                  style={{
                    fontFamily: "JetBrains Mono",
                    fontSize: 14,
                    borderRadius: 2,
                    color: "#1A1814",
                  }}
                />
                <View className="flex-row gap-sm">
                  <Pressable
                    className="flex-1 py-[10px] items-center"
                    style={{ backgroundColor: "#1A4FBF", borderRadius: 4 }}
                    disabled={correctMutation.isPending}
                    onPress={() => {
                      const edits: Record<string, unknown> = {};
                      if (editTitle !== commitment.title) edits.title = editTitle;
                      if (editAmount) {
                        const paise = Math.round(parseFloat(editAmount) * 100);
                        if (paise !== commitment.amount_paise)
                          edits.amount_paise = paise;
                      }
                      correctMutation.mutate({ action: "edit", edits });
                    }}
                  >
                    <Text style={{ fontFamily: "DM Sans Medium", fontSize: 14, color: "#FFFFFF" }}>
                      Submit correction
                    </Text>
                  </Pressable>
                  <Pressable
                    className="py-[10px] px-lg items-center"
                    onPress={() => setCorrectionMode(null)}
                  >
                    <Text style={{ fontFamily: "DM Sans", fontSize: 14, color: "#6B6456" }}>
                      Cancel
                    </Text>
                  </Pressable>
                </View>
              </View>
            )}

            {correctMutation.isError && (
              <Text
                className="mt-sm"
                style={{ fontFamily: "DM Sans", fontSize: 12, color: "#B91C1C" }}
              >
                Correction failed.
              </Text>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
