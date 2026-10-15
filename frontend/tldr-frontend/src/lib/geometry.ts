export type Rotation = 0 | 90 | 180 | 270

export type RectLike = {
  left: number
  top: number
  width: number
  height: number
}

export type Point = { x: number; y: number }

export function rotatedSize(width: number, height: number, rotation: Rotation) {
  return rotation === 90 || rotation === 270
    ? { width: height, height: width }
    : { width, height }
}

export function rotationTransform(width: number, height: number, rotation: Rotation) {
  if (rotation === 90) return `translate(${height} 0) rotate(90)`
  if (rotation === 180) return `translate(${width} ${height}) rotate(180)`
  if (rotation === 270) return `translate(0 ${width}) rotate(270)`
  return undefined
}

export function sourceToRotated(
  point: Point,
  width: number,
  height: number,
  rotation: Rotation,
): Point {
  if (rotation === 90) return { x: height - point.y, y: point.x }
  if (rotation === 180) return { x: width - point.x, y: height - point.y }
  if (rotation === 270) return { x: point.y, y: width - point.x }
  return point
}

export function rotatedToSource(
  point: Point,
  width: number,
  height: number,
  rotation: Rotation,
): Point {
  if (rotation === 90) return { x: point.y, y: height - point.x }
  if (rotation === 180) return { x: width - point.x, y: height - point.y }
  if (rotation === 270) return { x: width - point.y, y: point.x }
  return point
}

export function clientToNormalized(
  client: Point,
  rect: RectLike,
  sourceWidth: number,
  sourceHeight: number,
  rotation: Rotation,
): Point {
  const rotated = rotatedSize(sourceWidth, sourceHeight, rotation)
  const displayPoint = {
    x: ((client.x - rect.left) / rect.width) * rotated.width,
    y: ((client.y - rect.top) / rect.height) * rotated.height,
  }
  const source = rotatedToSource(displayPoint, sourceWidth, sourceHeight, rotation)
  return {
    x: clamp(source.x / sourceWidth),
    y: clamp(source.y / sourceHeight),
  }
}

export function normalizedRect(a: Point, b: Point) {
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    width: Math.abs(a.x - b.x),
    height: Math.abs(a.y - b.y),
  }
}

function clamp(value: number) {
  return Math.min(1, Math.max(0, value))
}
