import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { SettingsMenu } from "./SettingsMenu";
import { DEFAULT_FORCES } from "./graphForces";

const meta: Meta<typeof SettingsMenu> = {
  title: "Domain/SettingsMenu",
  component: SettingsMenu,
  args: {
    trailStyle: { thickness: "fine", style: "hand", wobble: 0.6, pressure: 0.4, lifecycleEdges: "all" },
    // Required by the Graph tab. Its absence went unnoticed because only a
    // story that actually NAVIGATES to that tab renders the panel that reads
    // it — which is exactly what the keyboard-navigation story does.
    graphSettings: {
      dragResponse: "reheat",
      forces: DEFAULT_FORCES,
      showOrphans: true,
      minConfidence: 0,
      showDecisions: false,
    },
    dock: "auto",
    theme: "light",
    onTrailStyle: fn(),
    onGraphSettings: fn(),
    onDock: fn(),
    onTheme: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof SettingsMenu>;

export const Closed: Story = {};

export const OpenTrailTab: Story = {
  play: async ({ canvasElement, step }) => {
    const canvas = within(canvasElement);
    await step("open the menu", async () => {
      await userEvent.click(canvas.getByRole("button", { name: "Settings" }));
      await expect(canvas.getByRole("dialog", { name: "Settings" })).toBeVisible();
    });
    await step("Trail tab is selected by default", async () => {
      const trailTab = canvas.getByRole("tab", { name: "Trail" });
      await expect(trailTab).toHaveAttribute("aria-selected", "true");
    });
  },
};

export const KeyboardTabNavigation: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Settings" }));
    const trailTab = canvas.getByRole("tab", { name: "Trail" });
    trailTab.focus();
    // Roving-tabindex tablist: ArrowRight moves focus and selection together.
    // Order is Trail, Graph, Inspector, Appearance — this asserted Inspector
    // until the Graph tab was inserted between the two, at which point the
    // story started rendering the Graph panel and crashing on the
    // graphSettings the meta never supplied.
    await userEvent.keyboard("{ArrowRight}");
    await expect(canvas.getByRole("tab", { name: "Graph" })).toHaveAttribute("aria-selected", "true");
    await expect(canvas.getByRole("tabpanel")).toHaveTextContent("Drag response");
    // Second press reaches Inspector, so the original assertion is kept rather
    // than dropped — the tablist must still traverse the whole way.
    await userEvent.keyboard("{ArrowRight}");
    await expect(canvas.getByRole("tab", { name: "Inspector" })).toHaveAttribute("aria-selected", "true");
    await expect(canvas.getByRole("tabpanel")).toHaveTextContent("Dock position");
  },
};

export const EscapeClosesAndReturnsFocus: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const trigger = canvas.getByRole("button", { name: "Settings" });
    await userEvent.click(trigger);
    await expect(canvas.getByRole("dialog")).toBeVisible();
    await userEvent.keyboard("{Escape}");
    await expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
    await expect(trigger).toHaveFocus();
  },
};

export const HandDrawnRevealsWobbleAndPressure: Story = {
  args: {
    trailStyle: { thickness: "fine", style: "hand", wobble: 0.6, pressure: 0.4, lifecycleEdges: "all" },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Settings" }));
    await expect(canvas.getByLabelText("Wobble")).toBeInTheDocument();
    await expect(canvas.getByLabelText("Pressure")).toBeInTheDocument();
  },
};

export const SlickStyleHidesWobbleAndPressure: Story = {
  args: {
    trailStyle: { thickness: "fine", style: "slick", wobble: 0.6, pressure: 0.4, lifecycleEdges: "all" },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Settings" }));
    await expect(canvas.queryByLabelText("Wobble")).not.toBeInTheDocument();
  },
};

export const DarkTheme: Story = {
  args: {
    theme: "dark",
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Settings" }));
    await userEvent.click(canvas.getByRole("tab", { name: "Appearance" }));
    await expect(canvas.getByRole("button", { name: "Dark" })).toHaveAttribute("aria-pressed", "true");
  },
};
