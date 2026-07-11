/**
 * Home screen — Daily brief + commitment ledger.
 *
 * DESIGN.md: Receipt density, 6–7 cards per screen on 360px phone.
 * DM Sans for UI, JetBrains Mono for amounts/dates/IDs/state.
 * No shadows, no skeleton loaders (use dashes), no avatars.
 */

import { useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { CommitmentCard } from "@/components/CommitmentCard";
import { StateFilter } from "@/components/StateFilter";
import { DailyBrief } from "@/components/DailyBrief";
import { fetchCommitments, fetchContexts, type Commitment } from "@/api/client";
import { useAppStore } from "@/store/app";
import { useContextSync } from "@/hooks/useContextSync";

/** Context selector (OL-043): horizontal pills to switch context. */
function ContextSelector() {
  const { principalId, selectedContextId, setSelectedContextId } = useAppStore();
  const { data: contexts } = useQuery({
    queryKey: ["contexts"],
    queryFn: () => fetchContexts(principalId!),
    enabled: !!principalId,
  });

  if (!contexts || contexts.length <= 1) return null;

  return (
    <View className="px-4 py-xs">
      <Text
        className="text-text-muted mb-xs"
        style={{ fontFamily: "DM Sans SemiBold", fontSize: 11, letterSpacing: 0.88 }}
      >
        CONTEXT
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <Pressable
          onPress={() => setSelectedContextId(null)}
          className="mr-sm"
          style={{
            backgroundColor: selectedContextId === null ? "#1A4FBF" : "#F3F4F6",
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
              color: selectedContextId === null ? "#FFFFFF" : "#374151",
            }}
          >
            ALL
          </Text>
        </Pressable>
        {contexts.map((ctx) => {
          const active = selectedContextId === ctx.id;
          return (
            <Pressable
              key={ctx.id}
              onPress={() => setSelectedContextId(active ? null : ctx.id)}
              className="mr-sm"
              style={{
                backgroundColor: active ? "#1A4FBF" : "#F3F4F6",
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
                  color: active ? "#FFFFFF" : "#374151",
                }}
              >
                {(ctx.label || ctx.type).toUpperCase()}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

export default function HomeScreen() {
  const { principalId, stateFilter, selectedContextId } = useAppStore();
  useContextSync(selectedContextId);

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["commitments", stateFilter, selectedContextId],
    queryFn: () =>
      fetchCommitments({
        principalId: principalId!,
        state: stateFilter ?? undefined,
        contextId: selectedContextId ?? undefined,
      }),
    enabled: !!principalId,
  });

  const commitments = data?.items ?? [];

  const renderItem = useCallback(
    ({ item }: { item: Commitment }) => (
      <Pressable onPress={() => router.push({ pathname: "/commitment-detail", params: { id: item.id } })}>
        <CommitmentCard commitment={item} />
      </Pressable>
    ),
    [],
  );

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={["top"]}>
      {/* Header */}
      <View className="px-4 py-3 border-b border-border flex-row justify-between items-center">
        <Text
          className="text-accent tracking-[0.08em]"
          style={{ fontFamily: "JetBrains Mono SemiBold", fontSize: 13 }}
        >
          OPENLNK
        </Text>
        <Pressable
          onPress={() => router.push("/create-commitment")}
          style={{
            backgroundColor: "#1A4FBF",
            borderRadius: 4,
            paddingHorizontal: 12,
            paddingVertical: 6,
          }}
        >
          <Text style={{ fontFamily: "DM Sans Medium", fontSize: 13, color: "#FFFFFF" }}>
            Create
          </Text>
        </Pressable>
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
            <ContextSelector />
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
