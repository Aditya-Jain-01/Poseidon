import { useEffect, useRef, useState } from 'react';
import { computeWorkspaceColumns } from './columns';

export function useWorkspaceLayout(detailsOpen) {
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.innerWidth <= 760);
  const [sidebarPreferred, setSidebarPreferred] = useState(320);
  const [detailsPreferred, setDetailsPreferred] = useState(380);
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef(null);
  const frameRef = useRef(0);
  const previousMobileRef = useRef(window.innerWidth <= 760);
  const desktopCollapsedRef = useRef(false);

  useEffect(() => {
    const onResize = () => {
      const nowMobile = window.innerWidth <= 760;
      if (nowMobile !== previousMobileRef.current) {
        if (nowMobile) {
          setSidebarCollapsed((wasCollapsed) => {
            desktopCollapsedRef.current = wasCollapsed;
            return true;
          });
        } else {
          setSidebarCollapsed(desktopCollapsedRef.current);
        }
        previousMobileRef.current = nowMobile;
      }
      setViewportWidth(window.innerWidth);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => () => cancelAnimationFrame(frameRef.current), []);

  const columns = computeWorkspaceColumns({
    viewportWidth,
    sidebarPreferred,
    detailsPreferred,
    sidebarCollapsed,
    detailsOpen,
  });

  const applyDrag = (clientX) => {
    const drag = dragRef.current;
    if (!drag) return;
    const offset = clientX - drag.startX;
    if (drag.side === 'sidebar') setSidebarPreferred(drag.startWidth + offset);
    else setDetailsPreferred(drag.startWidth - offset);
  };

  const beginResize = (side) => (event) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      side,
      pointerId: event.pointerId,
      startX: event.clientX,
      startWidth: side === 'sidebar' ? columns.sidebar : columns.details,
      latestX: event.clientX,
    };
    setDragging(true);
  };

  const moveResize = (event) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    drag.latestX = event.clientX;
    if (frameRef.current) return;
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = 0;
      applyDrag(drag.latestX);
    });
  };

  const endResize = (event) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    cancelAnimationFrame(frameRef.current);
    frameRef.current = 0;
    applyDrag(event.clientX);
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    setDragging(false);
  };

  const keyboardResize = (side) => (event) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    const amount = (event.shiftKey ? 32 : 16) * (event.key === 'ArrowRight' ? 1 : -1);
    if (side === 'sidebar') setSidebarPreferred((value) => value + amount);
    else setDetailsPreferred((value) => value - amount);
  };

  return {
    columns,
    sidebarCollapsed,
    toggleSidebar: () => setSidebarCollapsed((value) => !value),
    dragging,
    sidebarResize: { onPointerDown: beginResize('sidebar'), onPointerMove: moveResize, onPointerUp: endResize, onPointerCancel: endResize, onKeyDown: keyboardResize('sidebar') },
    detailsResize: { onPointerDown: beginResize('details'), onPointerMove: moveResize, onPointerUp: endResize, onPointerCancel: endResize, onKeyDown: keyboardResize('details') },
  };
}
