/**
 * State filter chips for commitment list.
 * ALL-CAPS JetBrains Mono labels per DESIGN.md.
 */

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import { stateColors, fonts, type CommitmentState } from "@openlnk/ui";

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

interface StateFilterProps {
  selected: string | null;
  onChange: (state: string | null) => void;
}

export default function StateFilter({ selected, onChange }: StateFilterProps) {
  return (
    <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap", mb: 2 }}>
      <Chip
        label="ALL"
        size="small"
        variant={selected === null ? "filled" : "outlined"}
        onClick={() => onChange(null)}
        sx={{
          fontFamily: fonts.mono,
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.1em",
          borderRadius: "9999px",
        }}
      />
      {STATES.map((s) => {
        const sc = stateColors[s];
        const isSelected = selected === s;
        return (
          <Chip
            key={s}
            label={sc.label}
            size="small"
            variant={isSelected ? "filled" : "outlined"}
            onClick={() => onChange(isSelected ? null : s)}
            sx={{
              fontFamily: fonts.mono,
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.1em",
              borderRadius: "9999px",
              color: sc.text,
              bgcolor: isSelected ? sc.background : "transparent",
              borderColor: isSelected ? sc.leftBar : "divider",
            }}
          />
        );
      })}
    </Box>
  );
}
