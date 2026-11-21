export const CENTER_MIN_WIDTH = 480;
const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 360;
const DETAILS_MIN_WIDTH = 280;
const DETAILS_MAX_WIDTH = 850;
const MOBILE_BREAKPOINT = 760;

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export function computeWorkspaceColumns({
  viewportWidth,
  sidebarPreferred = 320,
  detailsPreferred = 380,
  sidebarCollapsed = false,
  detailsOpen = false,
}) {
  const mobile = viewportWidth <= MOBILE_BREAKPOINT;
  const rail = 0;
  const sidebarLimit = mobile ? Math.min(viewportWidth * .8, SIDEBAR_MAX_WIDTH) : SIDEBAR_MAX_WIDTH;
  let sidebar = sidebarCollapsed ? (mobile ? 0 : 56) : clamp(sidebarPreferred, SIDEBAR_MIN_WIDTH, sidebarLimit);
  let details = detailsOpen ? clamp(detailsPreferred, DETAILS_MIN_WIDTH, Math.min(DETAILS_MAX_WIDTH, viewportWidth * .65)) : 0;
  const detailsOverlay = mobile || (detailsOpen && viewportWidth < rail + SIDEBAR_MIN_WIDTH + CENTER_MIN_WIDTH + DETAILS_MIN_WIDTH);

  if (!mobile) {
    const available = Math.max(0, viewportWidth - rail - CENTER_MIN_WIDTH);
    if (!sidebarCollapsed) sidebar = Math.min(sidebar, available);
    if (detailsOpen && !detailsOverlay) {
      details = Math.min(details, Math.max(DETAILS_MIN_WIDTH, available - sidebar));
      sidebar = Math.min(sidebar, available - details);
    }
  }

  return {
    rail,
    sidebar,
    details,
    detailsOverlay,
    gridSidebar: mobile ? 0 : sidebar,
    gridDetails: detailsOverlay ? 0 : details,
  };
}
