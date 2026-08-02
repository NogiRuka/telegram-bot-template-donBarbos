**Comparison target**

- Source visual truth: `C:/Users/Alviss/Downloads/ChatGPT Image 2026年8月2日 17_51_18.png`
- Implementation route: `/emby-metadata`
- Intended viewport: desktop, three-column workbench.

**Findings**

- [P1] Browser-rendered comparison is pending.
  Location: authenticated `/emby-metadata` route.
  Evidence: the app requires an authenticated session and no test administrator credentials were available to open the route in the local preview.
  Impact: the layout cannot yet be visually compared against the source at the same viewport.
  Fix: sign in locally, capture the workbench at desktop width, then compare the screenshot against the supplied reference and refine any P1/P2 differences.

**Required fidelity surfaces**

- Fonts and typography: implemented with the existing application font stack; browser comparison pending.
- Spacing and layout rhythm: three-column grid, toolbar, queue table, candidate cards, and writeback footer implemented; browser comparison pending.
- Colors and visual tokens: existing shadcn neutral, blue, emerald, and amber tokens used; browser comparison pending.
- Image quality and asset fidelity: real candidate image URLs are rendered when supplied by the data source; no synthetic poster placeholders are used.
- Copy and content: Chinese Emby metadata workflow copy is implemented.

**Implementation checklist**

- [x] Add authenticated metadata-workbench route and sidebar entry.
- [x] Add queue, search, candidate detail, and confirmed-writeback API endpoints.
- [x] Add interactive selection, filtering, overwrite mode, and field selection UI.
- [ ] Complete browser visual QA with an authenticated local session.

final result: blocked
