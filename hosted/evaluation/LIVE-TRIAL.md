# Prepared authenticated trial — not started

This procedure is prepared for the next human checkpoint. P0.2 stops before every authentication or mutation step.

## Preconditions

1. Use a disposable GitHub OAuth application and synthetic decision content only.
2. Confirm the application identifier in the live thread; do not store it in repository files.
3. Obtain explicit live permission to begin device-flow sign-in.
4. Keep the resulting token outside the repository and dispose of it after the trial.

## Trial sequence after approval

1. Start device-flow sign-in with the supplied disposable application identifier.
2. Have the user complete GitHub sign-in and verify the returned identity.
3. Capture one synthetic hard marker and one synthetic soft marker through the local adapter.
4. Generate inert, source-linked drafts and present the proposed approval mutation.
5. Stop again for explicit human approval before executing that mutation.
6. Verify audit coordinates, approval identity, idempotency, and token disposal.

No OAuth application identifier has been requested or used, no device flow has started, no approval mutation has
been presented or executed, and no OAuth token has been stored.
