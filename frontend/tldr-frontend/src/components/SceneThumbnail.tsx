import { useId, type ReactNode } from 'react'
import type { LessonScene } from '../types'
import { plotPath, timingPath } from '../lib/preview'
import { MathText } from './MathText'

export type SourceThumbnail = { url: string; width: number; height: number; crop: { x: number; y: number; width: number; height: number } }

export function SceneThumbnail({ scene, sourceImages = {} }: { scene: LessonScene; sourceImages?: Record<string, SourceThumbnail> }) {
  const clipId = `source-crop-${useId().replace(/:/g, '')}`
  const object = scene.objects[0]
  if (object?.kind === 'equation' && object.latex) return <figure className="scene-thumbnail"><figcaption>Typeset equation · {object.calculation ? 'calculation attached' : 'notation only'}{scene.objects.length > 1 ? ` · first of ${scene.objects.length}` : ''}</figcaption><div className="scene-equation-preview"><MathText text={`\\[${object.latex}\\]`} /></div></figure>
  let drawing: ReactNode = <text x="110" y="60" textAnchor="middle" className="thumb-label">Visual data not available</text>
  if (object) {
    const nodes = object.nodes ?? []
    if (object.kind === 'source_image' && object.source_ref) {
      const source = sourceImages[object.source_ref]
      drawing = source && source.width > 0 && source.height > 0 && source.crop.width > 0 && source.crop.height > 0
        ? <svg x="8" y="8" width="204" height="96" viewBox={`${source.crop.x * source.width} ${source.crop.y * source.height} ${source.crop.width * source.width} ${source.crop.height * source.height}`} preserveAspectRatio="xMidYMid meet" overflow="hidden"><defs><clipPath id={clipId} clipPathUnits="userSpaceOnUse"><rect x={source.crop.x * source.width} y={source.crop.y * source.height} width={source.crop.width * source.width} height={source.crop.height * source.height} /></clipPath></defs><image href={source.url} width={source.width} height={source.height} clipPath={`url(#${clipId})`} /></svg>
        : <><rect x="24" y="19" width="172" height="76" rx="5" className="thumb-node" />
        <text x="110" y="49" textAnchor="middle" className="thumb-text strong">Original course visual</text>
        <text x="110" y="70" textAnchor="middle" className="thumb-label">{object.source_ref}</text>
        {!!object.overlays?.length && <text x="110" y="88" textAnchor="middle" className="thumb-label">{object.overlays.length} display overlay{object.overlays.length === 1 ? '' : 's'}</text>}</>
    } else if (object.kind === 'timing' && object.signals?.length) {
      drawing = object.signals.map((signal, index, signals) => <g key={signal.name} transform={`translate(0 ${index * (90 / signals.length)})`}>
        <text x="8" y="24" className="thumb-label">{signal.name.slice(0, 12)}</text>
        <path d={timingPath(signal.values, 28)} className="thumb-line" />
      </g>)
    } else if (object.kind === 'plot') {
      const path = plotPath(object.points ?? [])
      if (path) drawing = <><path d="M 18 88 H 205 M 18 88 V 17" className="thumb-axis" /><path d={path} className="thumb-line" /><text x="110" y="107" textAnchor="middle" className="thumb-label">Scaled to source data range</text></>
    } else if (object.kind === 'geometry') {
      if (object.shape === 'circle') drawing = <circle cx="110" cy="57" r="32" className="thumb-shape" />
      else if (object.shape === 'triangle') drawing = <polygon points="110,20 65,88 155,88" className="thumb-shape" />
      else if (object.shape === 'rectangle') drawing = <rect x="62" y="28" width="96" height="58" className="thumb-shape" />
    } else if (object.kind === 'bus' && nodes.length === 2) {
      drawing = <><rect x="8" y="28" width="58" height="52" className="thumb-node" /><rect x="154" y="28" width="58" height="52" className="thumb-node" />
        <text x="37" y="56" textAnchor="middle" className="thumb-text">{nodes[0].slice(0, 12)}</text><text x="183" y="56" textAnchor="middle" className="thumb-text">{nodes[1].slice(0, 12)}</text>
        <path d="M 66 35 H 154 l -5 -3 m 5 3 l -5 3 M 66 55 H 154 l -5 -3 m 5 3 l -5 3 M 154 75 H 66 l 5 -3 m -5 3 l 5 3" className="thumb-line" />
        <text x="110" y="29" textAnchor="middle" className="thumb-label">Address</text><text x="110" y="49" textAnchor="middle" className="thumb-label">Read request</text><text x="110" y="95" textAnchor="middle" className="thumb-label">Return data</text></>
    } else if (object.kind === 'circuit' && nodes.length === 2) {
      drawing = <><path d="M 50 46 V 20 H 170 V 42 M 170 72 V 92 H 50 V 60 M 36 46 H 64 M 43 60 H 57" className="thumb-line" /><rect x="162" y="42" width="16" height="30" className="thumb-node" />
        <text x="30" y="42" className="thumb-label">+</text><text x="72" y="50" className="thumb-label">{nodes[0].slice(0, 12)}</text><text x="110" y="84" className="thumb-label">{nodes[1].slice(0, 12)}</text></>
    } else if (object.kind === 'process' && nodes.length) {
      drawing = nodes.map((node, index) => {
        const width = 200 / nodes.length
        return <g key={`${node}-${index}`}><rect x={10 + index * width} y="38" width={width - 8} height="35" rx="4" className="thumb-node" /><text x={10 + index * width + (width - 8) / 2} y="59" textAnchor="middle" className="thumb-text">{node.slice(0, 9)}</text>{index < nodes.length - 1 && <path d={`M ${2 + (index + 1) * width} 55 h 8 l -3 -3 m 3 3 l -3 3`} className="thumb-line" />}</g>
      })
    } else if (['text', 'equation'].includes(object.kind)) {
      drawing = <text x="110" y="58" textAnchor="middle" className="thumb-text strong">{(object.text || object.label).slice(0, 32)}</text>
    }
  }
  const provenance = object?.kind === 'source_image' ? 'original source' : object?.calculation && object.calculation.kind !== 'biology_concept' ? 'verified tool' : 'conceptual'
  return <figure className="scene-thumbnail"><figcaption>{object?.kind === 'source_image' ? 'Source reference' : 'Schematic preview'} · {provenance}{scene.objects.length > 1 ? ` · first of ${scene.objects.length}` : ''}</figcaption><svg viewBox="0 0 220 112" role="img" aria-label={`${provenance} reference for ${scene.title}`}><rect width="220" height="112" rx="10" fill="#173532" />{drawing}</svg></figure>
}
