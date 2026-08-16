import { Button } from "@/components/ui";
import type { BetListStatus, PaginatedBets } from "@/lib/types";

const statuses: Array<{ label: string; value: BetListStatus }> = [
  { label: "All statuses", value: "all" },
  { label: "Open", value: "open" },
  { label: "Closed", value: "closed" },
  { label: "Resolved", value: "resolved" },
];

export function BetListControls({
  data,
  disabled,
  onPageChange,
  onStatusChange,
  status,
}: {
  data?: PaginatedBets;
  disabled: boolean;
  onPageChange: (page: number) => void;
  onStatusChange: (status: BetListStatus) => void;
  status: BetListStatus;
}) {
  const page = data?.page ?? 1;
  const totalPages = data?.total_pages ?? 0;

  return (
    <div className="bet-list-controls">
      <label>
        <span>Filter by status</span>
        <select
          className="select"
          onChange={(event) =>
            onStatusChange(event.target.value as BetListStatus)
          }
          value={status}
        >
          {statuses.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <div className="pagination-controls">
        <span className="muted">
          {data?.total ?? 0} {(data?.total ?? 0) === 1 ? "market" : "markets"} · Page {page}
          {totalPages > 0 ? ` of ${totalPages}` : ""}
        </span>
        <Button
          className="secondary compact"
          disabled={disabled || page <= 1}
          onClick={() => onPageChange(page - 1)}
          type="button"
        >
          Previous
        </Button>
        <Button
          className="secondary compact"
          disabled={disabled || totalPages === 0 || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          Next
        </Button>
      </div>
    </div>
  );
}
