import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CreateBetForm } from "./create-bet-form";

afterEach(cleanup);

describe("CreateBetForm", () => {
  it("accepts the default whole-number LMSR liquidity", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <CreateBetForm />
      </QueryClientProvider>,
    );

    const input = screen.getByLabelText("LMSR liquidity (b)");
    expect(input).toHaveValue(100);
    expect(input).toHaveAttribute("min", "0.01");
    expect(input).toHaveAttribute("step", "0.01");
    expect(input).toBeValid();
  });

  it("shows display names when limiting visibility", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <CreateBetForm
          groupId="group-1"
          members={[
            {
              user_id: "11111111-1111-1111-1111-111111111111",
              display_name: "Fatimah",
              role: "member",
              status: "active",
              joined_at: "2030-01-01T00:00:00Z",
              removed_at: null,
            },
          ]}
        />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByLabelText("Limit visibility to selected members"));

    expect(screen.getByLabelText("Fatimah")).toBeInTheDocument();
    expect(screen.queryByText(/11111111/)).not.toBeInTheDocument();
  });
});
