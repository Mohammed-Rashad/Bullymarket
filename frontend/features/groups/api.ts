import { apiFetch } from "@/lib/api-client";
import type { Group, GroupMember } from "@/lib/types";

export function listGroups() {
  return apiFetch<Group[]>("/groups");
}

export function createGroup(input: {
  name: string;
  description?: string;
  image_url?: string;
}) {
  return apiFetch<Group>("/groups", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function joinGroup(invite_code: string) {
  return apiFetch<Group>("/groups/join", {
    method: "POST",
    body: JSON.stringify({ invite_code }),
  });
}

export function listMembers(groupId: string) {
  return apiFetch<GroupMember[]>(`/groups/${groupId}/members`);
}

export function removeMember(groupId: string, userId: string) {
  return apiFetch<GroupMember>(`/groups/${groupId}/members/${userId}`, {
    method: "DELETE",
  });
}
