import { useEffect, useRef, type ReactNode } from 'react'

export function CourseSidebar({ open, narrow, onClose, children }: {
  open: boolean
  narrow: boolean
  onClose: () => void
  children: ReactNode
}) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open || !narrow) return
    const background = Array.from(document.querySelectorAll<HTMLElement>('.topbar, .workspace-nav, .workspace-body'))
    const previous = background.map((element) => element.hasAttribute('inert'))
    background.forEach((element) => element.setAttribute('inert', ''))
    panelRef.current?.querySelector<HTMLButtonElement>('[aria-label="Close course sidebar"]')?.focus()
    return () => background.forEach((element, index) => { if (!previous[index]) element.removeAttribute('inert') })
  }, [open, narrow])

  return <>
    {open && narrow && <div className="course-sidebar-backdrop" aria-hidden="true" onClick={onClose} />}
    <div ref={panelRef} className={`shared-course-sidebar ${narrow ? 'drawer' : 'docked'}`} hidden={!open}
      role={narrow ? 'dialog' : undefined} aria-modal={narrow && open ? true : undefined} aria-label={narrow ? 'Course navigation' : undefined}
      onKeyDown={(event) => {
        if (event.defaultPrevented) return
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); onClose(); return }
        if (event.key !== 'Tab' || !narrow) return
        const controls = Array.from(panelRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), a[href], [tabindex="0"]') ?? []).filter((element) => element.getClientRects().length)
        const first = controls[0]
        const last = controls[controls.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }}>{children}</div>
  </>
}
