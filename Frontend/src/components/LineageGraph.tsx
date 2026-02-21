import { Link } from 'react-router-dom'
import { useMemo } from 'react'

interface Node {
  id: string
  label: string
  type: string
  columns: string[]
  primary_keys: string[]
}

interface Edge {
  source: string
  target: string
  type: string
  columns: string[]
  referred_columns: string[]
}

interface LineageGraphProps {
  nodes: Node[]
  edges: Edge[]
}

const NODE_WIDTH = 140
const NODE_HEIGHT = 48
const PADDING = 24
const GAP = 60

export default function LineageGraph({ nodes, edges }: LineageGraphProps) {
  const { positions, width, height } = useMemo(() => {
    const pos: Record<string, { x: number; y: number }> = {}
    const cols = Math.ceil(Math.sqrt(nodes.length)) || 1
    nodes.forEach((n, i) => {
      const col = i % cols
      const row = Math.floor(i / cols)
      pos[n.id] = {
        x: PADDING + col * (NODE_WIDTH + GAP),
        y: PADDING + row * (NODE_HEIGHT + GAP),
      }
    })
    const last = nodes[nodes.length - 1]
    const lastPos = last ? pos[last.id] : { x: PADDING, y: PADDING }
    return {
      positions: pos,
      width: lastPos.x + NODE_WIDTH + PADDING,
      height: lastPos.y + NODE_HEIGHT + PADDING,
    }
  }, [nodes])

  const edgePath = (e: Edge) => {
    const src = positions[e.source]
    const tgt = positions[e.target]
    if (!src || !tgt) return ''
    const sx = src.x + NODE_WIDTH / 2
    const sy = src.y + NODE_HEIGHT
    const tx = tgt.x + NODE_WIDTH / 2
    const ty = tgt.y
    const mid = (sy + ty) / 2
    return `M ${sx} ${sy} C ${sx} ${mid}, ${tx} ${mid}, ${tx} ${ty}`
  }

  return (
    <div style={{ overflow: 'auto', maxHeight: '70vh' }}>
      <svg width={width} height={height} style={{ minWidth: width }}>
        <defs>
          <marker
            id="arrow"
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8" />
          </marker>
        </defs>
        {edges.map((e, i) => (
          <path
            key={i}
            d={edgePath(e)}
            fill="none"
            stroke="#94a3b8"
            strokeWidth="1.5"
            markerEnd="url(#arrow)"
          />
        ))}
        {nodes.map((n) => {
          const pos = positions[n.id]
          if (!pos) return null
          return (
            <foreignObject
              key={n.id}
              x={pos.x}
              y={pos.y}
              width={NODE_WIDTH}
              height={NODE_HEIGHT}
            >
              <Link
                to={`/table/${encodeURIComponent(n.id)}`}
                style={{
                  display: 'block',
                  width: '100%',
                  height: '100%',
                  padding: '8px 12px',
                  background: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontFamily: 'ui-monospace, monospace',
                  textDecoration: 'none',
                  color: '#334155',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {n.label}
              </Link>
            </foreignObject>
          )
        })}
      </svg>
    </div>
  )
}
