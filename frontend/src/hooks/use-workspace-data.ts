"use client";

import * as React from "react";

import { streamEvents } from "@/lib/api";
import { useAnalysesStore } from "@/stores/analyses";
import { useMatrixStore } from "@/stores/matrix";
import { useQAStore } from "@/stores/qa";
import { useSessionStore } from "@/stores/session";
import { useNotificationsStore } from "@/stores/workspace";
import { loadWorkspace } from "@/stores/workspace-lifecycle";
import type { AppNotification } from "@/types";

/**
 * Fetches the org's collections once there is a session to fetch them with, and
 * keeps the notification bell live for as long as the workspace is mounted.
 */
export function useWorkspaceData() {
  const authed = useSessionStore((s) => s.isAuthenticated);
  const receive = useNotificationsStore((s) => s.receive);

  React.useEffect(() => {
    if (!authed) return;
    void loadWorkspace();
  }, [authed]);

  React.useEffect(() => {
    if (!authed) return;
    const stream = streamEvents("/api/v1/notifications/stream", (event) => {
      // The stream carries whole notification records, not agent events.
      if (typeof event.id === "string" && typeof event.title === "string") {
        receive(event as unknown as AppNotification);
      }
    });
    return stream.stop;
  }, [authed, receive]);
}

/**
 * The matrix and the question set are fetched per analysis rather than for the
 * whole org — a capture lead opens one bid at a time, and the rows behind the
 * other twelve are not worth the round trip.
 */
export function useAnalysisData(analysisId: string | undefined) {
  const authed = useSessionStore((s) => s.isAuthenticated);
  const refreshAnalysis = useAnalysesStore((s) => s.refreshOne);
  const loadMatrix = useMatrixStore((s) => s.load);
  const loadQuestions = useQAStore((s) => s.load);

  React.useEffect(() => {
    if (!authed || !analysisId) return;
    void refreshAnalysis(analysisId);
    void loadMatrix(analysisId);
    void loadQuestions(analysisId);
  }, [authed, analysisId, refreshAnalysis, loadMatrix, loadQuestions]);
}

/** The org-wide matrix needs every analysis's rows, not just one. */
export function useAllMatrixData() {
  const authed = useSessionStore((s) => s.isAuthenticated);
  const analysisIds = useAnalysesStore((s) => s.analyses.map((a) => a.id).join(","));
  const loadMatrix = useMatrixStore((s) => s.load);

  React.useEffect(() => {
    if (!authed || !analysisIds) return;
    for (const id of analysisIds.split(",")) void loadMatrix(id);
  }, [authed, analysisIds, loadMatrix]);
}
