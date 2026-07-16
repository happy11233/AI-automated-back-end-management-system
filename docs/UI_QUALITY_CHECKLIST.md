# UI Quality Checklist

## Product Benchmark

The interface should feel like a modern enterprise AI or SaaS admin console:

- Dense but readable
- Operational instead of marketing-like
- Consistent spacing
- Clear hierarchy
- Stable table and card dimensions
- Real loading, empty, error, and success states
- No overflow

The Page Quality Agent may reference Copilot Studio, Agentforce, ServiceNow AI Agent Studio, UiPath, Zendesk, and Intercom for structure and quality expectations.

## Navigation

- [ ] Navigation hierarchy is clear.
- [ ] Current page highlight is obvious.
- [ ] Side navigation does not crowd page content.
- [ ] Admin-only pages are hidden from employees.
- [ ] Position-specific pages are hidden from other positions.
- [ ] Parent menu and child menu behavior are consistent.
- [ ] URLs, refresh, and browser back/forward preserve page state.

## Cards

- [ ] Cards are used only for real information units or tools.
- [ ] No card inside another decorative card.
- [ ] Same card groups have equal height where expected.
- [ ] Titles, descriptions, metrics, and actions are aligned.
- [ ] Long text uses truncation, wrapping, or tooltip.
- [ ] Content stays inside card boundaries.
- [ ] Card radius and border style are consistent.

## Tables

- [ ] Column widths are predictable.
- [ ] Long IDs, filenames, URLs, ERP record names, and emails do not break layout.
- [ ] Action column stays stable.
- [ ] Empty state is clear.
- [ ] Loading state is visible.
- [ ] Error state does not cover unrelated content.
- [ ] Pagination or scrolling is available for long lists.

## Forms

- [ ] Inputs align across columns.
- [ ] Labels are readable.
- [ ] Required and optional fields are clear.
- [ ] Disabled, loading, success, and failure states are visible.
- [ ] Dangerous actions require confirmation.
- [ ] Form buttons do not resize unpredictably.

## AI-Specific States

- [ ] Generating state is visible.
- [ ] Syncing and indexing states are visible.
- [ ] Evaluation running state is visible.
- [ ] Connector testing state is visible.
- [ ] Failed automation can show reason and retry action.
- [ ] AI output references are readable and not noisy.

## Responsive Checks

Required viewports:

- [ ] Desktop: 1440 x 900
- [ ] Laptop: 1280 x 800
- [ ] Tablet: 768 x 1024
- [ ] Mobile: 390 x 844

For each changed page:

- [ ] No global horizontal scroll.
- [ ] No card overflow.
- [ ] No table cell pushing page width.
- [ ] No button text overflow.
- [ ] Modals and drawers fit the screen.
- [ ] Primary action remains reachable.

## Visual Polish

- [ ] Palette is not dominated by one color family.
- [ ] Typography scale matches admin context.
- [ ] Icon use is consistent.
- [ ] Spacing feels intentional.
- [ ] Loading and empty states look professional.
- [ ] Screenshots look acceptable without explanation.

## Screenshot Evidence

For frontend loops, save screenshots under `/tmp` with descriptive names:

- Admin desktop
- Employee desktop
- Changed page desktop
- Changed page mobile
- Modal or drawer state when applicable

The final loop report must mention screenshot paths and whether overflow checks passed.

