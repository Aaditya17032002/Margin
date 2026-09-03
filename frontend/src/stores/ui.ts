import { create } from "zustand";

import type { Citation } from "@/types";

export interface RailSource {
  citation: Citation;
  analysisId: string;
  label: string;
  origin?: string;
}

interface UIState {
  /** What the Margin rail is currently showing. */
  source: RailSource | null;
  /** A pinned source survives hover changes until it is released. */
  pinned: boolean;
  railOpen: boolean;
  railFocused: boolean;
  commandOpen: boolean;
  shortcutsOpen: boolean;
  importOpen: boolean;
  recentCommands: string[];

  peek: (source: RailSource) => void;
  hold: (source: RailSource) => void;
  release: () => void;
  setPinned: (pinned: boolean) => void;
  closeRail: () => void;
  openRail: () => void;
  setRailFocused: (focused: boolean) => void;
  setCommandOpen: (open: boolean) => void;
  setShortcutsOpen: (open: boolean) => void;
  setImportOpen: (open: boolean) => void;
  rememberCommand: (id: string) => void;
}

export const useUIStore = create<UIState>((set, get) => ({
  source: null,
  pinned: false,
  railOpen: false,
  railFocused: false,
  commandOpen: false,
  shortcutsOpen: false,
  importOpen: false,
  recentCommands: [],

  /** Hover / focus preview — ignored while a source is pinned. */
  peek: (source) => {
    if (get().pinned) return;
    set({ source, railOpen: true });
  },

  /** Explicit selection — always wins, and pins the rail open. */
  hold: (source) => set({ source, railOpen: true, pinned: true }),

  release: () => {
    if (get().pinned) return;
    set({ source: null });
  },

  setPinned: (pinned) => set({ pinned }),
  closeRail: () => set({ railOpen: false, pinned: false, source: null, railFocused: false }),
  openRail: () => set({ railOpen: true }),
  setRailFocused: (railFocused) => set({ railFocused }),
  setCommandOpen: (commandOpen) => set({ commandOpen }),
  setShortcutsOpen: (shortcutsOpen) => set({ shortcutsOpen }),
  setImportOpen: (importOpen) => set({ importOpen }),

  rememberCommand: (id) =>
    set((state) => ({
      recentCommands: [id, ...state.recentCommands.filter((c) => c !== id)].slice(0, 5),
    })),
}));
