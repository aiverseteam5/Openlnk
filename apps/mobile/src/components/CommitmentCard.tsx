/**
 * CommitmentCard — per DESIGN.md card anatomy.
 *
 * [3px STATE BAR] | [ID in mono, muted]           [STATE BADGE in mono]
 *                 | [COMMITMENT TITLE in DM Sans 600]
 *                 | [Counterparty · Class]          [AMOUNT in mono]
 *                 | [Provenance tag]                [DUE DATE in mono]
 *
 * No shadows (DESIGN.md). Borders instead. 2px border radius.
 */

import { View, Text, Pressable } from "react-native";
import { stateColors, type CommitmentState } from "@openlnk/ui";
import type { Commitment } from "@/api/client";

function formatAmount(paise: number | null, currency: string): string {
  if (paise === null) return "";
  const amt = paise / 100;
  if (currency === "INR") return `\u20B9${amt.toLocaleString("en-IN")}`;
  return `${currency} ${amt.toFixed(2)}`;
}

function formatDue(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

export function CommitmentCard({ commitment: c }: { commitment: Commitment }) {
  const stateKey: CommitmentState = c.at_risk
    ? "overdue"
    : (c.state as CommitmentState);
  const sc = stateColors[stateKey] ?? stateColors.proposed;

  return (
    <Pressable className="mx-0">
      <View
        className="flex-row border border-border bg-surface overflow-hidden"
        style={{ borderRadius: 2 }}
      >
        {/* 3px state bar */}
        <View
          style={{ width: 3, backgroundColor: sc.leftBar }}
        />

        <View className="flex-1 px-md py-[10px]">
          {/* ID + State badge */}
          <View className="flex-row justify-between items-center mb-xs">
            <Text
              className="text-text-muted"
              style={{ fontFamily: "JetBrains Mono", fontSize: 10 }}
            >
              CMT-{c.id.slice(0, 4).toUpperCase()}
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
            className="mb-xs"
            numberOfLines={1}
            style={{
              fontFamily: "DM Sans SemiBold",
              fontSize: 14,
              lineHeight: 20,
              color: "#1A1814",
            }}
          >
            {c.title}
          </Text>

          {/* Counterparty · Class + Amount */}
          <View className="flex-row justify-between items-center">
            <Text
              className="text-text-muted"
              style={{ fontFamily: "DM Sans", fontSize: 12 }}
            >
              {c.counterparty_id
                ? `${c.counterparty_id.slice(0, 8)} \u00B7 ${c.class}`
                : c.class}
            </Text>
            {c.amount_paise !== null && (
              <Text
                style={{
                  fontFamily: "JetBrains Mono SemiBold",
                  fontSize: 15,
                  lineHeight: 20,
                  color: "#1A1814",
                }}
              >
                {formatAmount(c.amount_paise, c.currency)}
              </Text>
            )}
          </View>

          {/* Provenance + Due date */}
          <View className="flex-row justify-between items-center mt-xs">
            {c.provenance_kind ? (
              <Text
                className="text-text-muted"
                style={{ fontFamily: "DM Sans", fontSize: 11 }}
              >
                {c.provenance_kind}
              </Text>
            ) : (
              <View />
            )}
            {c.due_at ? (
              <Text
                className="text-text-muted"
                style={{ fontFamily: "JetBrains Mono", fontSize: 11 }}
              >
                Due {formatDue(c.due_at)}
              </Text>
            ) : null}
          </View>
        </View>
      </View>
    </Pressable>
  );
}
