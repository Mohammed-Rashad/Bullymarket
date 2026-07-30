"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import {
  Button,
  Card,
  EmptyState,
  ErrorNotice,
  Input,
  Loading,
} from "@/components/ui";
import {
  useCreateGroup,
  useGroups,
  useJoinGroup,
} from "@/features/groups/hooks";
import { errorMessage } from "@/lib/api-client";

export default function GroupsPage() {
  const groups = useGroups();
  const createGroup = useCreateGroup();
  const joinGroup = useJoinGroup();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [inviteCode, setInviteCode] = useState("");

  async function create(event: FormEvent) {
    event.preventDefault();
    await createGroup.mutateAsync({ name, description: description || undefined });
    setName("");
    setDescription("");
  }

  async function join(event: FormEvent) {
    event.preventDefault();
    await joinGroup.mutateAsync(inviteCode);
    setInviteCode("");
  }

  return (
    <>
      <header className="page-title">
        <div>
          <span className="eyebrow">Private rooms, isolated standings</span>
          <h1>Your groups</h1>
          <p>Each room keeps its own bets and realized win/loss leaderboard.</p>
        </div>
      </header>
      <div className="content-grid">
        <section className="stack">
          {groups.isLoading ? <Loading /> : null}
          {groups.error ? (
            <ErrorNotice message={errorMessage(groups.error)} />
          ) : null}
          {!groups.isLoading && !groups.data?.length ? (
            <EmptyState
              body="Create a room or use an invite code to join your friends."
              title="No groups yet"
            />
          ) : null}
          {groups.data?.map((group) => (
            <Link href={`/groups/${group.id}`} key={group.id}>
              <Card className="card-pad">
                <div className="section-heading">
                  <div>
                    <span className="scope-chip">
                      {group.membership_status === "removed"
                        ? "settlement only"
                        : group.role}
                    </span>
                    <h2 style={{ marginTop: 12 }}>{group.name}</h2>
                    <p className="muted" style={{ marginBottom: 0 }}>
                      {group.description ?? "A private BullyMarket room."}
                    </p>
                  </div>
                  <strong>→</strong>
                </div>
                {group.pending_settlement ? (
                  <div className="notice pending-notice" style={{ marginTop: 16 }}>
                    You were removed from this group. Only your existing open
                    positions remain available until they settle.
                  </div>
                ) : null}
              </Card>
            </Link>
          ))}
        </section>
        <aside className="stack">
          <Card className="card-pad">
            <h2>Create a group</h2>
            <p className="muted">You become the first admin.</p>
            <form className="form-stack" onSubmit={create}>
              <div className="field">
                <label htmlFor="group-name">Name</label>
                <Input
                  id="group-name"
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Thursday crew"
                  required
                  value={name}
                />
              </div>
              <div className="field">
                <label htmlFor="group-description">Description</label>
                <Input
                  id="group-description"
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Optional"
                  value={description}
                />
              </div>
              {createGroup.error ? (
                <ErrorNotice message={errorMessage(createGroup.error)} />
              ) : null}
              <Button disabled={createGroup.isPending} type="submit">
                Create room
              </Button>
            </form>
          </Card>
          <Card className="card-pad">
            <h2>Join with a code</h2>
            <p className="muted">Paste the invite code an admin shared.</p>
            <form className="form-stack" onSubmit={join}>
              <Input
                aria-label="Invite code"
                onChange={(event) => setInviteCode(event.target.value)}
                placeholder="Invite code"
                required
                value={inviteCode}
              />
              {joinGroup.error ? (
                <ErrorNotice message={errorMessage(joinGroup.error)} />
              ) : null}
              <Button
                className="secondary"
                disabled={joinGroup.isPending}
                type="submit"
              >
                Join group
              </Button>
            </form>
          </Card>
        </aside>
      </div>
    </>
  );
}

