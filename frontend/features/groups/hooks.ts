"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as groupsApi from "./api";

export function useGroups() {
  return useQuery({ queryKey: ["groups"], queryFn: groupsApi.listGroups });
}

export function useCreateGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: groupsApi.createGroup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["groups"] }),
  });
}

export function useJoinGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: groupsApi.joinGroup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["groups"] }),
  });
}

export function useGroupMembers(groupId: string, enabled = true) {
  return useQuery({
    queryKey: ["groups", groupId, "members"],
    queryFn: () => groupsApi.listMembers(groupId),
    enabled: Boolean(groupId) && enabled,
  });
}

export function useRemoveMember(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => groupsApi.removeMember(groupId, userId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["groups", groupId, "members"],
      }),
  });
}
