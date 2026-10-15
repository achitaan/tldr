import { useEffect, useRef, useState } from 'react'

export function ConfirmDialog({ title, message, confirmLabel, requiredText, busy = false, onCancel, onConfirm }: {
  title: string
  message: string
  confirmLabel: string
  requiredText?: string
  busy?: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  const [value, setValue] = useState('')
  const valid = !requiredText || value === requiredText
  const dialogRef = useRef<HTMLElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    if (!requiredText) cancelRef.current?.focus()
    return () => previousFocus.current?.focus()
  }, [requiredText])

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape' && !busy) { event.preventDefault(); onCancel(); return }
    if (event.key !== 'Tab') return
    const controls = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])') ?? [])
    if (!controls.length) return
    const first = controls[0]
    const last = controls[controls.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onCancel() }}>
      <section ref={dialogRef} className="modal small" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message" onKeyDown={handleKeyDown}>
        <header><div><span className="quiet-label">Please confirm</span><h2 id="confirm-title">{title}</h2></div></header>
        <p id="confirm-message">{message}</p>
        {requiredText && <label>Type <strong>{requiredText}</strong> to continue<input autoFocus value={value} onChange={(event) => setValue(event.target.value)} /></label>}
        <div className="button-row end"><button ref={cancelRef} className="button" type="button" disabled={busy} onClick={onCancel}>Cancel</button><button className="button danger" type="button" disabled={!valid || busy} onClick={onConfirm}>{busy ? 'Removing' : confirmLabel}</button></div>
      </section>
    </div>
  )
}
