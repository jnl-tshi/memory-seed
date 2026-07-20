import type { Preview } from "@storybook/react-vite";

import "../src/styles.css";

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },

    a11y: {
      // 'todo' - show a11y violations in the test UI only
      // 'error' - fail CI on a11y violations
      // 'off' - skip a11y checks entirely
      // Automated checks are necessary but not sufficient (WCAG 2.2 AA target,
      // memory-trace-frontend-architecture-and-design-system-proposal.md section 11)
      // - keep them as a hard gate so a violation fails the build.
      test: "error",
    },
  },
};

export default preview;
