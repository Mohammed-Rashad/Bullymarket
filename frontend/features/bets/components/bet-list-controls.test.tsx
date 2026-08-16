import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BetListControls } from "./bet-list-controls";

afterEach(cleanup);

describe("BetListControls", () => {
  it("changes status and pages using server pagination metadata", () => {
    const onPageChange = vi.fn();
    const onStatusChange = vi.fn();
    render(
      <BetListControls
        data={{ items: [], page: 2, page_size: 6, total: 13, total_pages: 3 }}
        disabled={false}
        onPageChange={onPageChange}
        onStatusChange={onStatusChange}
        status="all"
      />,
    );

    expect(screen.getByText("13 markets · Page 2 of 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.click(screen.getByRole("button", { name: "Resolved" }));
    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(onStatusChange).toHaveBeenCalledWith("resolved");
    expect(onPageChange).toHaveBeenNthCalledWith(1, 1);
    expect(onPageChange).toHaveBeenNthCalledWith(2, 3);
  });
});
