import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
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
});
