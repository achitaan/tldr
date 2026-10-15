import { describe, expect, it } from 'vitest'
import type { Citation, Source } from '../types'
import { sceneCitations } from './sceneSources'

const source: Source = { id: 1, course: 1, title: 'Buses', kind: 'pdf', status: 'ready', pages: [
  { id: 10, source: 1, number: 2, text: 'Read cycle', width: 1000, height: 1400, regions: [{ id: 20, page: 10, label: 'Clock', x: 0, y: 0, width: 1, height: 1, confirmed: true }] },
] }
const pageCitation: Citation = { source_id: 1, source_title: 'Buses', page_id: 10, page_number: 2, quote: 'Read cycle' }
const regionCitation = { ...pageCitation, region_id: 20 }

describe('active lesson scene references', () => {
  it('returns only recorded references for the current scene and removes duplicates', () => {
    expect(sceneCitations({ citations: [pageCitation, regionCitation, regionCitation] }, { source_refs: ['r20'] }, [source])).toEqual([regionCitation])
    expect(sceneCitations({ citations: [pageCitation, regionCitation] }, { source_refs: ['p10'] }, [source])).toEqual([pageCitation])
  })
  it('does not invent evidence from source labels or references outside the current course', () => {
    expect(sceneCitations({ citations: [] }, { source_refs: ['p10'] }, [source])).toEqual([])
    expect(sceneCitations({ citations: [pageCitation] }, { source_refs: ['p10'] }, [])).toEqual([])
    expect(sceneCitations({ citations: [{ ...pageCitation, source_id: 2 }] }, { source_refs: ['p10'] }, [source])).toEqual([])
  })
  it('drops references to removed regions rather than presenting their old quotes', () => {
    expect(sceneCitations({ citations: [{ ...regionCitation, region_id: 99 }] }, { source_refs: ['r99'] }, [source])).toEqual([])
  })
})
