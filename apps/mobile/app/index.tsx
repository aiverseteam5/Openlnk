/**
 * Home screen — Daily brief + commitment ledger.
 *
 * DESIGN.md: Receipt density, 6–7 cards per screen on 360px phone.
 * DM Sans for UI, JetBrains Mono for amounts/dates/IDs/state.
 * No shadows, no skeleton loaders (use dashes), no avatars.
 */

import { useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  Pressable,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import { CommitmentCard } from "@/components/CommitmentCard";
import { StateFilter } from "@/components/StateFilter";
import { DailyBrief } from "@/components/DailyBrief";
import { fetchCommitments, type Commitment } from "@/api/client";
import { useAppStore } from "@/store/app";

export default function HomeScreen() {
  const { stateFilter } = useAppStore();
  const [cursor, setCursor] = useState<string | undefined>();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["commitments", stateFilter],
    queryFn: () => fetchCommitments({ state: stateFilter ?? undefined }),
  });

  const commitments = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;

  const renderItem = useCallback(
    ({ item }: { item: Commitment }) => <CommitmentCard commitment={item} />,
    [],
  );

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={["top"]}>
      {/* Header */}
      <View className="px-4 py-3 border-b border-border">
        <Text
          className="text-accent tracking-[0.08em]"
          style={{ fontFamily: "JetBrains Mono SemiBold", fontSize: 13 }}
        >
          OPENLNK
        </Text>
      </View>

      <FlatList
        data={commitments}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={{ paddingVertical: 8 }}
        ItemSeparatorComponent={() => <View className="h-[8px]" />}
        ListHeaderComponent={
          <>
            <DailyBrief />
            <StateFilter />
          </>
        }
        ListEmptyComponent={
          isLoading ? (
            <Text
              className="text-text-muted text-center py-8"
              style={{ fontFamily: "DM Sans Medium", fontSize: 14 }}
            >
              {"\u2014"} Loading...
            </Text>
          ) : (
            <Text
              className="text-text-muted text-center py-8"
              style={{ fontFamily: "DM Sans Medium", fontSize: 14 }}
            >
              No commitments. Create one.
            </Text>
          )
        }
        onEndReached={() => {
          if (nextCursor) setCursor(nextCursor);
        }}
        onEndReachedThreshold={0.5}
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
