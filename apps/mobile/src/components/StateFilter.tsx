/**
 * StateFilter — horizontal chip row for filtering commitment state.
 * JetBrains Mono ALL-CAPS per DESIGN.md state badge spec.
 */

import { ScrollView, Pressable, Text, View } from "react-native";
import { stateColors, type CommitmentState } from "@openlnk/ui";
import { useAppStore } from "@/store/app";

const STATES: CommitmentState[] = [
  "proposed",
  "accepted",
  "in_progress",
  "done",
  "overdue",
  "broken",
  "fulfilled",
  "cancelled",
];

export function StateFilter() {
  const { stateFilter, setStateFilter } = useAppStore();

  return (
    <View className="px-4 py-sm">
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {/* All */}
        <Pressable
          onPress={() => setStateFilter(null)}
          className="mr-sm"
          style={{
            backgroundColor: stateFilter === null ? "#1A4FBF" : "#F3F4F6",
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
              color: stateFilter === null ? "#FFFFFF" : "#374151",
            }}
          >
            ALL
          </Text>
        </Pressable>

        {STATES.map((state) => {
          const sc = stateColors[state];
          const active = stateFilter === state;
          return (
            <Pressable
              key={state}
              onPress={() => setStateFilter(active ? null : state)}
              className="mr-sm"
              style={{
                backgroundColor: active ? sc.text : sc.background,
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
                  color: active ? "#FFFFFF" : sc.text,
                }}
              >
                {sc.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}
