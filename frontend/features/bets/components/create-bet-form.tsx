"use client";

import { FormEvent, useState } from "react";

import { Button, ErrorNotice, Input } from "@/components/ui";
import { ImagePicker } from "@/components/image-picker";
import { useUploadImage } from "@/features/media/hooks";
import { errorMessage } from "@/lib/api-client";
import type { GroupMember } from "@/lib/types";
import { useCreateBet } from "../hooks";

export function CreateBetForm({
  groupId,
  members = [],
  onCreated,
}: {
  groupId?: string;
  members?: GroupMember[];
  onCreated?: (betId: string) => void;
}) {
  const create = useCreateBet(groupId);
  const uploadImage = useUploadImage();
  const [question, setQuestion] = useState("");
  const [description, setDescription] = useState("");
  const [yesLabel, setYesLabel] = useState("Yes");
  const [noLabel, setNoLabel] = useState("No");
  const [endTime, setEndTime] = useState("");
  const [bLiquidity, setBLiquidity] = useState("100");
  const [restricted, setRestricted] = useState(false);
  const [visibleIds, setVisibleIds] = useState<string[]>([]);
  const [image, setImage] = useState<File | null>(null);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string>();

  async function submit(event: FormEvent) {
    event.preventDefault();
    let imageUrl = uploadedImageUrl;
    if (image && !imageUrl) {
      imageUrl = (await uploadImage.mutateAsync(image)).image_url;
      setUploadedImageUrl(imageUrl);
    }
    const bet = await create.mutateAsync({
      question,
      description: description || undefined,
      image_url: imageUrl,
      end_time: new Date(endTime).toISOString(),
      outcome_labels: [yesLabel, noLabel],
      b_liquidity: bLiquidity,
      ...(groupId && restricted ? { visible_to_user_ids: visibleIds } : {}),
    });
    setQuestion("");
    setDescription("");
    setImage(null);
    setUploadedImageUrl(undefined);
    onCreated?.(bet.id);
  }

  return (
    <form className="form-stack" onSubmit={submit}>
      <div className="field">
        <label htmlFor="question">Question</label>
        <Input
          id="question"
          maxLength={300}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Will Ahmed actually arrive before 8?"
          required
          value={question}
        />
      </div>
      <div className="field">
        <label htmlFor="description">Context (optional)</label>
        <textarea
          className="textarea"
          id="description"
          onChange={(event) => setDescription(event.target.value)}
          placeholder="What counts, where to verify, and any useful context."
          value={description}
        />
      </div>
      <ImagePicker
        file={image}
        label="Bet image"
        onChange={(file) => {
          setImage(file);
          setUploadedImageUrl(undefined);
        }}
      />
      <div className="form-row">
        <div className="field">
          <label htmlFor="outcome-a">First outcome</label>
          <Input
            id="outcome-a"
            maxLength={80}
            onChange={(event) => setYesLabel(event.target.value)}
            required
            value={yesLabel}
          />
        </div>
        <div className="field">
          <label htmlFor="outcome-b">Second outcome</label>
          <Input
            id="outcome-b"
            maxLength={80}
            onChange={(event) => setNoLabel(event.target.value)}
            required
            value={noLabel}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="end-time">Betting closes</label>
        <Input
          id="end-time"
          min={new Date().toISOString().slice(0, 16)}
          onChange={(event) => setEndTime(event.target.value)}
          required
          type="datetime-local"
          value={endTime}
        />
      </div>
      <div className="field">
        <label htmlFor="b-liquidity">LMSR liquidity (b)</label>
        <Input
          id="b-liquidity"
          min="0.01"
          onChange={(event) => setBLiquidity(event.target.value)}
          required
          step="0.01"
          type="number"
          value={bLiquidity}
        />
        <small className="muted">
          Higher values make prices move more slowly. Maximum house loss is b × ln(2).
        </small>
      </div>
      {groupId && members.length ? (
        <div className="field">
          <label>
            <input
              checked={restricted}
              onChange={(event) => setRestricted(event.target.checked)}
              type="checkbox"
            />{" "}
            Limit visibility to selected members
          </label>
          {restricted ? (
            <div className="stack">
              {members
                .filter((member) => member.status === "active")
                .map((member) => (
                  <label key={member.user_id}>
                    <input
                      checked={visibleIds.includes(member.user_id)}
                      onChange={(event) =>
                        setVisibleIds((current) =>
                          event.target.checked
                            ? [...current, member.user_id]
                            : current.filter((id) => id !== member.user_id),
                        )
                      }
                      type="checkbox"
                    />{" "}
                    {member.display_name}
                  </label>
                ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {create.error ? (
        <ErrorNotice message={errorMessage(create.error)} />
      ) : null}
      {uploadImage.error ? (
        <ErrorNotice message={errorMessage(uploadImage.error)} />
      ) : null}
      <Button disabled={create.isPending || uploadImage.isPending} type="submit">
        {uploadImage.isPending
          ? "Uploading image…"
          : create.isPending
            ? "Opening market…"
            : "Open market"}
      </Button>
    </form>
  );
}
