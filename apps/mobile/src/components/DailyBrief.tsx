/**
 * DailyBrief — collapsed summary card at top of home screen.
 *
 * DESIGN.md: at-risk count, due-today count, awaiting-action count.
 * No skeleton loaders — use dashes for loading state.
 * Shows AI-generated summary when available.
 */

import { View, Text } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { fetchCommitments, fetchBriefSummary } from "@/api/client";
import { useAppStore } from "@/store/app";

function StatBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <View className="flex-1 items-center py-sm">
      <Text
        style={{
          fontFamily: "JetBrains Mono SemiBold",
          fontSize: 20,
          lineHeight: 28,
          color: color ?? "#1A1814",
        }}
      >
        {value}
      </Text>
      <Text
        className="text-text-muted mt-[2px]"
        style={{
          fontFamily: "DM Sans",
          fontSize: 11,
          letterSpacing: 0.88,
        }}
      >
        {label}
      </Text>
    </View>
  );
}

export function DailyBrief() {
  const { principalId } = useAppStore();
  const { data, isLoading } = useQuery({
    queryKey: ["commitments", "brief"],
    queryFn: () => fetchCommitments({ principalId, limit: 100 }),
  });

  const { data: briefData } = useQuery({
    queryKey: ["brief-summary"],
    queryFn: () => fetchBriefSummary(principalId),
    staleTime: 5 * 60 * 1000,
  });

  const items = data?.items ?? [];
  const atRisk = items.filter((c) => c.at_risk).length;
  const proposed = items.filter((c) => c.state === "proposed").length;

  const today = new Date().toISOString().slice(0, 10);
  const dueToday = items.filter(
    (c) => c.due_at && c.due_at.slice(0, 10) === today,
  ).length;

  const dash = "\u2014";

  return (
    <View className="mx-4 mt-sm mb-xs border border-border bg-surface" style={{ borderRadius: 2 }}>
      <View className="px-md py-sm border-b border-border">
        <Text
          style={{
            fontFamily: "DM Sans SemiBold",
            fontSize: 11,
            letterSpacing: 0.88,
            color: "#6B6456",
          }}
        >
          DAILY BRIEF
        </Text>
      </View>

      {/* AI Summary */}
      {briefData?.summary ? (
        <View className="px-md py-sm border-b border-border" style={{ borderLeftWidth: 3, borderLeftColor: "#1A4FBF" }}>
          <Text
            style={{
              fontFamily: "DM Sans",
              fontSize: 13,
              lineHeight: 20,
              color: "#1A1814",
            }}
          >
            {briefData.summary}
          </Text>
        </View>
      ) : null}

      <View className="flex-row">
        <StatBox label="AT RISK" value={isLoading ? dash : String(atRisk)} color={atRisk > 0 ? "#92600A" : undefined} />
        <View className="w-[1px] bg-border" />
        <StatBox label="DUE TODAY" value={isLoading ? dash : String(dueToday)} />
        <View className="w-[1px] bg-border" />
        <StatBox label="AWAITING" value={isLoading ? dash : String(proposed)} />
      </View>
    </View>
  );
}
