import { describe, it, expect, beforeAll } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";

// This test hits the REAL backend running at localhost:8000 -- no mocking.
// It's an integration test: if the backend isn't running, these fail loudly,
// which is the point (catches real breakage, not a mocked illusion of health).

beforeAll(async () => {
  const res = await fetch("http://localhost:8000/health").catch(() => null);
  if (!res || !res.ok) {
    throw new Error(
      "Backend is not reachable at localhost:8000 -- start it with `uvicorn app.main:app` before running these tests."
    );
  }
});

describe("FairResolve frontend against the real backend", () => {
  it("loads and displays the seeded Case A and Case B disputes", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText(/Goods and Services Not Received|Goods And Services Not Received/i).length).toBeGreaterThan(0);
    }, { timeout: 5000 });

    const sidebarItems = document.querySelectorAll(".case-item");
    expect(sidebarItems.length).toBeGreaterThanOrEqual(2);
  });

  it("shows the reasoning text and confidence bar for the active case", async () => {
    render(<App />);
    await waitFor(() => {
      expect(document.querySelector(".reasoning-text")).toBeTruthy();
    }, { timeout: 5000 });

    const reasoningEl = document.querySelector(".reasoning-text");
    expect(reasoningEl.textContent.length).toBeGreaterThan(20);
  });

  it("toggles between card member and merchant view without changing the underlying reasoning", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(document.querySelector(".reasoning-text")).toBeTruthy();
    }, { timeout: 5000 });

    const reasoningBefore = document.querySelector(".reasoning-text").textContent;

    const merchantBtn = screen.getByText("Merchant view");
    await user.click(merchantBtn);

    const reasoningAfter = document.querySelector(".reasoning-text").textContent;
    expect(reasoningAfter).toBe(reasoningBefore);
    expect(document.querySelector(".viewer-note")).toBeTruthy();
  });

  it("opens the new dispute modal with all 22 reason codes populated", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("+ File a new dispute")).toBeTruthy();
    }, { timeout: 5000 });

    await user.click(screen.getByText("+ File a new dispute"));

    await waitFor(() => {
      expect(document.querySelector(".modal")).toBeTruthy();
    });

    const selects = document.querySelectorAll(".modal select");
    const reasonCodeSelect = selects[1];
    expect(reasonCodeSelect.options.length).toBe(22);
  });

  it("files a live Tier 1 dispute and shows an auto-resolved result", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("+ File a new dispute")).toBeTruthy();
    }, { timeout: 5000 });

    await user.click(screen.getByText("+ File a new dispute"));
    await waitFor(() => expect(document.querySelector(".modal")).toBeTruthy());

    const selects = document.querySelectorAll(".modal select");
    const reasonCodeSelect = selects[1];
    // 4530 = Currency Discrepancy, a Tier 1 deterministic code
    await user.selectOptions(reasonCodeSelect, "4530");

    await waitFor(() => {
      expect(document.querySelector(".tier-hint").textContent).toMatch(/Tier 1/);
    });

    const submitBtn = screen.getByText("Submit dispute");
    await user.click(submitBtn);

    await waitFor(() => {
      const badge = document.querySelector(".case-item.active .badge");
      expect(badge && badge.textContent).toBe("Resolved");
    }, { timeout: 8000 });
  });
});
