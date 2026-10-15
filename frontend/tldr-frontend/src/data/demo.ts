import type { Course, CourseBundle, Message, ServiceStatus } from '../types'
import { openingLesson, openingSource } from './showcase'

export const demoCourses: Course[] = [
  {
    id: 'demo-transport',
    name: 'Systems in motion',
    description: 'A visual course on rates, feedback, and connected systems.',
  },
  {
    id: 'demo-biology',
    name: 'Cellular signals',
    description: 'A compact set of biology reading notes.',
  },
]

export const demoStatus: ServiceStatus = {
  provider: 'demo',
  model: 'curated samples',
  generation_enabled: false,
  configuration_issues: [],
  quota_paused: false,
  ocr_available: true,
  embedding_enabled: false,
  worker: 'demo mode',
}

export const demoBundle: CourseBundle = {
  sources: [
    {
      id: 'source-bus',
      course: 'demo-transport',
      title: 'Processor bus timing notes',
      kind: 'image',
      status: 'ready',
      pages: [{
        id: 'page-bus',
        source: 'source-bus',
        number: 1,
        width: 1200,
        height: 800,
        demo_kind: 'bus',
        text: 'The processor places address 16 on the address bus, then asserts a read request. Memory drives the data bus and marks the value valid. The processor samples 42 only after the valid signal, then releases the request.',
        original_text: 'The processor places address 16 on the address bus, then asserts a read request. Memory drives the data bus and marks the value valid. The processor samples 42 only after the valid signal, then releases the request.',
        regions: [
          { id: 'region-bus-gap', page: 'page-bus', label: 'Valid sampling window', x: 0.34, y: 0.27, width: 0.38, height: 0.36, text: 'The processor samples 42 only after the valid signal.', confirmed: true },
        ],
      }],
    },
    {
      id: 'source-math',
      course: 'demo-transport',
      title: 'Rate of change sketch',
      kind: 'image',
      status: 'ready',
      pages: [{
        id: 'page-math',
        source: 'source-math',
        number: 1,
        width: 1200,
        height: 800,
        demo_kind: 'math',
        text: 'The slope of a distance-time graph is speed. A steeper tangent means a larger instantaneous speed. A horizontal segment means the object is stopped even while time continues.',
        original_text: 'The slope of a distance-time graph is speed. A steeper tangent means a larger instantaneous speed. A horizontal segment means the object is stopped even while time continues.',
        regions: [
          { id: 'region-math-slope', page: 'page-math', label: 'Tangent slope', x: 0.39, y: 0.22, width: 0.34, height: 0.42, text: 'A steeper tangent means a larger instantaneous speed.', confirmed: true },
        ],
      }],
    },
    {
      id: 'source-finance',
      course: 'demo-transport',
      title: 'Compound growth worksheet',
      kind: 'image',
      status: 'ready',
      pages: [{
        id: 'page-finance',
        source: 'source-finance',
        number: 1,
        width: 1200,
        height: 800,
        demo_kind: 'finance',
        text: 'Compound growth applies the rate to the updated balance. Over repeated periods, the amount added each time increases because prior growth is included in the next base.',
        original_text: 'Compound growth applies the rate to the updated balance. Over repeated periods, the amount added each time increases because prior growth is included in the next base.',
        regions: [
          { id: 'region-finance-curve', page: 'page-finance', label: 'Compounding curve', x: 0.32, y: 0.2, width: 0.45, height: 0.53, text: 'Compound growth applies the rate to the updated balance.', confirmed: true },
        ],
      }],
    },
    {
      id: 'source-biology',
      course: 'demo-transport',
      title: 'Cell membrane pathways',
      kind: 'image',
      status: 'ready',
      pages: [{
        id: 'page-biology',
        source: 'source-biology',
        number: 1,
        width: 1200,
        height: 800,
        demo_kind: 'biology',
        text: 'A receptor changes shape when a matching signal binds. That change starts a relay inside the cell. The response can be amplified because one activated protein can affect many downstream molecules.',
        original_text: 'A receptor changes shape when a matching signal binds. That change starts a relay inside the cell. The response can be amplified because one activated protein can affect many downstream molecules.',
        regions: [
          { id: 'region-bio-receptor', page: 'page-biology', label: 'Membrane receptor', x: 0.38, y: 0.27, width: 0.2, height: 0.38, text: 'A receptor changes shape when a matching signal binds.', confirmed: true },
        ],
      }],
    },
  ],
  conversations: [{ id: 'conversation-demo', course: 'demo-transport', title: 'Course questions' }],
  lessons: [{
    id: 'lesson-demo',
    course: 'demo-transport',
    title: 'A pedagogical bus read',
    revisions: [{
      id: 'revision-demo',
      lesson: 'lesson-demo',
      number: 1,
      citations: [],
      spec: {
        title: 'A pedagogical bus read',
        target_minutes: 15,
        learning_objectives: [
          'Separate the address from the value returned by memory.',
          'Identify when a processor may safely sample the data bus.',
        ],
        chapters: [
          {
            id: 'read-cycle',
            title: 'One read transaction',
            objective: 'Follow a simplified processor and memory handshake.',
            start_seconds: 0,
            end_seconds: 45.351021,
            scenes: [
              {
                id: 'request',
                title: 'The processor asks for a value',
                objective: 'Distinguish the address from the returned data.',
                narration: 'The processor places an address on the address bus. It then asserts a read request. The address identifies where to read; it is not the value being returned.',
                source_refs: ['original-bus-fixture'],
                objects: [
                  {"id": "read-path", "kind": "bus", "label": "Read request: address 16", "nodes": ["Processor", "Memory"], "calculation": {"kind": "bus_read", "inputs": {"address": 16, "value": 42, "width": 8}}},
                ],
                steps: [
                  { object_ids: ['read-path'], caption: 'Present address 16, then request a read.' },
                ],
                start_seconds: 0,
                end_seconds: 20.900998,
              },
              {
                id: 'sample',
                title: 'Sample only when data is valid',
                objective: 'Read the control signals before sampling data.',
                narration: 'Memory drives the data bus and signals that the value is valid. The processor samples forty two only after that indication. Sampling early can capture an old or unstable value.',
                source_refs: ['original-bus-fixture'],
                objects: [
                  {"id": "handshake", "kind": "timing", "label": "Simplified read handshake", "signals": [{"name": "Read request", "values": [0, 1, 1, 1, 0, 0]}, {"name": "Data valid", "values": [0, 0, 1, 1, 0, 0]}, {"name": "Sample", "values": [0, 0, 0, 1, 0, 0]}], "calculation": {"kind": "bus_read", "inputs": {"address": 16, "value": 42, "width": 8}}},
                ],
                steps: [{ object_ids: ['handshake'], caption: 'Wait for valid data, sample, then release.' }],
                start_seconds: 20.900998,
                end_seconds: 45.351021,
              },
            ],
          },
        ],
      },
      video_url: '/sample/bus.mp4',
      captions_url: '/sample/captions.vtt',
      transcript_url: '/sample/transcript.txt',
      poster_url: '/sample/poster.jpg',
      manifest: {
        duration_seconds: 45.42127,
        warnings: ['Actual narration is 0.8 minutes; requested 15. No artificial padding was added.'],
        chapters: [{ id: 'read-cycle', title: 'One read transaction', start_seconds: 0, end_seconds: 45.351021 }],
        scenes: [
          { scene_id: 'request', chapter_id: 'read-cycle', title: 'The processor asks for a value', start_seconds: 0, end_seconds: 20.900998, source_refs: ['original-bus-fixture'], objects: [{"id": "read-path", "kind": "bus", "label": "Read request: address 16", "nodes": ["Processor", "Memory"], "calculation": {"kind": "bus_read", "inputs": {"address": 16, "value": 42, "width": 8}}}] },
          { scene_id: 'sample', chapter_id: 'read-cycle', title: 'Sample only when data is valid', start_seconds: 20.900998, end_seconds: 45.351021, source_refs: ['original-bus-fixture'], objects: [{"id": "handshake", "kind": "timing", "label": "Simplified read handshake", "signals": [{"name": "Read request", "values": [0, 1, 1, 1, 0, 0]}, {"name": "Data valid", "values": [0, 0, 1, 1, 0, 0]}, {"name": "Sample", "values": [0, 0, 0, 1, 0, 0]}], "calculation": {"kind": "bus_read", "inputs": {"address": 16, "value": 42, "width": 8}}}] },
        ],
      },
    }],
  }],
  jobs: [
    { id: 'job-complete', course: 'demo-transport', kind: 'render', status: 'complete', progress: 100, result: { revision_id: 'revision-demo' } },
  ],
  studyItems: [
    { id: 'study-flash', course: 'demo-transport', kind: 'flashcard', title: 'Address bus', body: 'What information travels on the address bus?', data: { answer: 'The location the processor wants to read, not the returned value.' }, completed: false },
    { id: 'study-quiz', course: 'demo-transport', kind: 'quiz', title: 'Sampling check', body: 'When should the processor sample the data bus?', data: { options: ['After data valid', 'As soon as address appears', 'After request releases'], answer: 'After data valid', attempts: [] }, completed: false },
    { id: 'study-check', course: 'demo-transport', kind: 'checklist', title: 'Trace a read', body: 'Use the source visual and lesson.', data: { items: [{ text: 'Place the address', done: true }, { text: 'Assert the read request', done: false }, { text: 'Wait for valid data', done: false }] }, completed: false },
    { id: 'study-bookmark', course: 'demo-transport', kind: 'bookmark', title: 'Read timing visual', body: 'Return to the highlighted sampling window.', data: {}, page: 'page-bus', completed: false },
    { id: 'study-confusion', course: 'demo-transport', kind: 'confusion', title: 'Address versus data', body: 'I still mix up the location being requested and the value being returned.', data: {}, completed: false },
  ],
}

export const demoMessages: Message[] = [
  {
    id: 'message-user',
    conversation: 'conversation-demo',
    role: 'user',
    content: 'Why can the processor not sample 42 as soon as it places address 16?',
    citations: [],
    status: 'complete',
    curated: true,
  },
  {
    id: 'message-assistant',
    conversation: 'conversation-demo',
    role: 'assistant',
    content: 'Address 16 identifies the location to read. It does not guarantee that memory has already driven 42 onto the data bus. The processor waits for the valid signal so it does not capture an old or unstable value.',
    citations: [{
      page_id: 'page-bus',
      source_id: 'source-bus',
      source_title: 'Processor bus timing notes',
      page_number: 1,
      quote: 'The processor samples 42 only after the valid signal.',
      region_id: 'region-bus-gap',
    }],
    status: 'complete',
    curated: true,
  },
]

export function bundleForDemoCourse(courseId: Course['id']): CourseBundle {
  if (courseId === 'demo-transport') return { ...demoBundle, sources: [openingSource, ...demoBundle.sources], lessons: [openingLesson, ...demoBundle.lessons] }
  return {
    ...demoBundle,
    sources: demoBundle.sources.filter((source) => source.id === 'source-biology').map((source) => ({ ...source, course: courseId })),
    conversations: [],
    lessons: [],
    jobs: [],
    studyItems: [],
  }
}
