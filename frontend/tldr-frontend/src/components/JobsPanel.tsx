import { IconAlertTriangle, IconCheck, IconClockPause, IconPlayerPlay, IconRefresh, IconX } from '../icons'
import { api } from '../lib/api'
import type { Job, ServiceStatus } from '../types'

export function JobsPanel({ jobs, status, demo, onClose, onJobsChange, onStatusChange, onNotice }: {
  jobs: Job[]
  status?: ServiceStatus
  demo: boolean
  onClose: () => void
  onJobsChange: (jobs: Job[]) => void
  onStatusChange: (status: ServiceStatus) => void
  onNotice: (message: string) => void
}) {
  const update = (next: Job) => onJobsChange(jobs.map((job) => job.id === next.id ? next : job))
  const act = async (job: Job, action: 'cancel' | 'retry') => {
    if (demo) { onNotice('Demo jobs are static examples.'); return }
    try {
      update(action === 'cancel' ? await api.cancelJob(job.id) : await api.retryJob(job.id))
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Job could not be updated.')
    }
  }
  const resume = async () => {
    if (demo) return
    try {
      onStatusChange(await api.resumeService())
      onNotice('Generation resumed. Retry each paused job when ready.')
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Generation could not be resumed.')
    }
  }

  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <aside className="jobs-panel" role="dialog" aria-modal="true" aria-labelledby="activity-heading">
        <header><div><span className="quiet-label">Background work</span><h2 id="activity-heading">Activity</h2></div><button className="icon-button" type="button" aria-label="Close activity" onClick={onClose}><IconX size={19} /></button></header>
        {status?.quota_paused && <div className="service-warning"><IconClockPause size={20} aria-hidden="true" /><div><strong>Generation is paused</strong><p>Review the configuration, then explicitly resume before retrying jobs.</p><button className="button compact" type="button" onClick={resume}>Resume generation</button></div></div>}
        {status && !status.generation_enabled && !demo && <div className="service-warning"><IconAlertTriangle size={20} aria-hidden="true" /><div><strong>Generation is not configured</strong><p>{status.configuration_issues.join(' ') || 'Check the local service configuration.'}</p></div></div>}
        <div className="job-list">
          {jobs.length === 0 ? <p className="empty-copy">No course jobs yet.</p> : jobs.map((job) => (
            <article className="job-row" key={job.id}>
              <div className={`job-icon ${job.status}`}>{job.status === 'complete' ? <IconCheck size={18} /> : job.status === 'failed' ? <IconAlertTriangle size={18} /> : <IconRefresh size={18} />}</div>
              <div><strong>{job.kind}</strong><span>{job.status}{job.status === 'running' ? `, ${Math.round(job.progress)}%` : ''}</span>{job.error && <small>{job.error}</small>}</div>
              <div className="job-actions">{(['queued', 'running'] as Job['status'][]).includes(job.status) && <button className="button compact" type="button" onClick={() => void act(job, 'cancel')}>Cancel</button>}{(['failed', 'paused'] as Job['status'][]).includes(job.status) && <button className="button compact" type="button" onClick={() => void act(job, 'retry')}><IconPlayerPlay size={15} aria-hidden="true" /> Retry</button>}</div>
            </article>
          ))}
        </div>
      </aside>
    </div>
  )
}
