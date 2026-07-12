/**
 * Extraction inbox — AI-extracted commitments awaiting review.
 *
 * Shows proposed commitments with provenance_kind set (extracted, not manual).
 * Inline accept/reject with confidence display (OL-020, OL-021, OL-022, OL-026).
 *
 * DESIGN.md: state bar, mono confidence, DM Sans UI, no shadows.
 */

import { useCallback } from "react";
import { View, Text, FlatList, Pressable, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchCommitments,
  transitionState,
  correctCommitment,
  type Commitment,
} from "@/api/client";
import { useAppStore } from "@/store/app";

const STATE_COLOR = "#7C8894"; // proposed state bar

function confidenceColor(confidence: number): string {
  if (confidence >= 0.95) return "#2E7D32";
  if (confidence >= 0.85) return "#92600A";
  return "#C62828";
}

function formatAmount(paise: number | null, currency: string): string {
  if (paise === null) return "";
  const amount = paise / 100;
  if (currency === "INR") return `\u20B9${amount.toLocaleString("en-IN")}`;
  return `${currency} ${amount.toFixed(2)}`;
}

function formatDue(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

function ExtractionCard({
  commitment,
  onAccept,
  onReject,
  isPending,
}: {
  commitment: Commitment;
  onAccept: () => void;
  onReject: () => void;
  isPending: boolean;
}) {
  const confidence = commitment.extraction_confidence ?? 0;

  return (
    <View
      style={{
        flexDirection: "row",
        borderWidth: 1,
        borderColor: "#D6D0C4",
        borderRadius: 2,
        backgroundColor: "#FFFFFF",
        marginHorizontal: 16,
        overflow: "hidden",
      }}
    >
      {/* 3px state bar */}
      <View style={{ width: 3, backgroundColor: STATE_COLOR }} />

      <View style={{ flex: 1, paddingHorizontal: 12, paddingVertical: 10 }}>
        {/* Row 1: Provenance + Confidence */}
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 4,
          }}
        >
          <Text
            style={{
              fontFamily: "JetBrains Mono",
              fontSize: 10,
              letterSpacing: 0.8,
              color: "#6B7280",
              textTransform: "uppercase",
            }}
          >
            {commitment.provenance_kind}
          </Text>
          <Text
            style={{
              fontFamily: "JetBrains Mono SemiBold",
              fontSize: 11,
              color: confidenceColor(confidence),
            }}
          >
            {(confidence * 100).toFixed(0)}%
          </Text>
        </View>

        {/* Row 2: Title */}
        <Pressable
          onPress={() =>
            router.push({
              pathname: "/commitment-detail",
              params: { id: commitment.id },
            })
          }
        >
          <Text
            numberOfLines={2}
            style={{
              fontFamily: "DM Sans SemiBold",
              fontSize: 14,
              lineHeight: 20,
              color: "#1A1814",
              marginBottom: 4,
            }}
          >
            {commitment.title}
          </Text>
        </Pressable>

        {/* Row 3: Class + Amount + Due */}
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 8,
          }}
        >
          <Text
            style={{
              fontFamily: "DM Sans",
              fontSize: 12,
              color: "#6B7280",
            }}
          >
            {commitment.class}
          </Text>
          <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
            {commitment.amount_paise !== null && (
              <Text
                style={{
                  fontFamily: "JetBrains Mono SemiBold",
                  fontSize: 14,
                  color: "#1A1814",
                }}
              >
                {formatAmount(commitment.amount_paise, commitment.currency)}
              </Text>
            )}
            {commitment.due_at && (
              <Text
                style={{
                  fontFamily: "JetBrains Mono",
                  fontSize: 11,
                  color: "#6B7280",
                }}
              >
                {formatDue(commitment.due_at)}
              </Text>
            )}
          </View>
        </View>

        {/* Action buttons */}
        <View style={{ flexDirection: "row", gap: 8 }}>
          <Pressable
            onPress={onAccept}
            disabled={isPending}
            style={{
              flex: 1,
              backgroundColor: isPending ? "#9CA3AF" : "#1A4FBF",
              borderRadius: 4,
              paddingVertical: 8,
              alignItems: "center",
            }}
          >
            <Text
              style={{
                fontFamily: "DM Sans SemiBold",
                fontSize: 13,
                color: "#FFFFFF",
              }}
            >
              Accept
            </Text>
          </Pressable>
          <Pressable
            onPress={onReject}
            disabled={isPending}
            style={{
              flex: 1,
              borderWidth: 1,
              borderColor: isPending ? "#9CA3AF" : "#C62828",
              borderRadius: 4,
              paddingVertical: 8,
              alignItems: "center",
            }}
          >
            <Text
              style={{
                fontFamily: "DM Sans SemiBold",
                fontSize: 13,
                color: isPending ? "#9CA3AF" : "#C62828",
              }}
            >
              Reject
            </Text>
          </Pressable>
          <Pressable
            onPress={() =>
              router.push({
                pathname: "/commitment-detail",
                params: { id: commitment.id },
              })
            }
            style={{
              borderWidth: 1,
              borderColor: "#D6D0C4",
              borderRadius: 4,
              paddingVertical: 8,
              paddingHorizontal: 12,
              alignItems: "center",
            }}
          >
            <Text
              style={{
                fontFamily: "DM Sans SemiBold",
                fontSize: 13,
                color: "#374151",
              }}
            >
              Edit
            </Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

export default function ExtractionInboxScreen() {
  const { principalId, selectedContextId } = useAppStore();
  const queryClient = useQueryClient();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["commitments", "proposed", selectedContextId, "inbox"],
    queryFn: () =>
      fetchCommitments({
        principalId,
        state: "proposed",
        contextId: selectedContextId ?? undefined,
        limit: 100,
      }),
  });

  const extracted =
    data?.items.filter((c) => c.provenance_kind !== null) ?? [];

  const acceptMutation = useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) =>
      transitionState(principalId, id, "accepted", version),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) =>
      correctCommitment(principalId, id, { action: "reject" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  const isPending = acceptMutation.isPending || rejectMutation.isPending;

  const renderItem = useCallback(
    ({ item }: { item: Commitment }) => (
      <ExtractionCard
        commitment={item}
        isPending={isPending}
        onAccept={() =>
          acceptMutation.mutate({ id: item.id, version: item.version })
        }
        onReject={() => rejectMutation.mutate(item.id)}
      />
    ),
    [isPending, acceptMutation, rejectMutation],
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#F5F2EC" }} edges={["top"]}>
      {/* Header */}
      <View
        style={{
          paddingHorizontal: 16,
          paddingVertical: 12,
          borderBottomWidth: 1,
          borderBottomColor: "#D6D0C4",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <View>
          <Text
            style={{
              fontFamily: "DM Sans SemiBold",
              fontSize: 18,
              color: "#1A1814",
            }}
          >
            Extraction Inbox
          </Text>
          <Text
            style={{
              fontFamily: "DM Sans",
              fontSize: 12,
              color: "#6B7280",
            }}
          >
            AI-extracted commitments awaiting review
          </Text>
        </View>
        <Pressable onPress={() => router.back()}>
          <Text
            style={{
              fontFamily: "JetBrains Mono SemiBold",
              fontSize: 11,
              color: "#6B7280",
              letterSpacing: 0.5,
            }}
          >
            BACK
          </Text>
        </Pressable>
      </View>

      {(acceptMutation.isError || rejectMutation.isError) && (
        <View style={{ paddingHorizontal: 16, paddingTop: 8 }}>
          <Text style={{ fontFamily: "DM Sans", fontSize: 12, color: "#C62828" }}>
            Action failed. The commitment may have been updated.
          </Text>
        </View>
      )}

      <FlatList
        data={extracted}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={{ paddingVertical: 8 }}
        ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
        ListEmptyComponent={
          isLoading ? (
            <Text
              style={{
                fontFamily: "DM Sans Medium",
                fontSize: 14,
                color: "#6B7280",
                textAlign: "center",
                paddingVertical: 48,
              }}
            >
              {"\u2014"} Loading...
            </Text>
          ) : (
            <Text
              style={{
                fontFamily: "DM Sans Medium",
                fontSize: 14,
                color: "#6B7280",
                textAlign: "center",
                paddingVertical: 48,
              }}
            >
              No pending extractions.
            </Text>
          )
        }
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor="#1A4FBF"
          />
        }
      />
    </SafeAreaView>
  );
}
