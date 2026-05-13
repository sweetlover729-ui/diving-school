'use client'

import React, { useRef, useEffect, useState } from 'react'

interface Props {
  onSave: (dataUrl: string) => void
  width?: number
  height?: number
}

export default function SignatureCanvas({ onSave, width = 400, height = 150 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [hasSignature, setHasSignature] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.strokeStyle = '#1c1d1f'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    // 画背景格线
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctx.strokeStyle = '#e0e0e0'
    for (let y = 0; y < height; y += 20) {
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(width, y)
      ctx.stroke()
    }
    for (let x = 0; x < width; x += 20) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height)
      ctx.stroke()
    }
  }, [width, height])

  const getPos = (e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    if ('touches' in e) {
      return {
        x: (e.touches[0].clientX - rect.left) * scaleX,
        y: (e.touches[0].clientY - rect.top) * scaleY,
      }
    }
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    }
  }

  const start = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx) return
    setIsDrawing(true)
    const pos = getPos(e)
    ctx.beginPath()
    ctx.moveTo(pos.x, pos.y)
  }

  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing) return
    e.preventDefault()
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx) return
    const pos = getPos(e)
    ctx.lineTo(pos.x, pos.y)
    ctx.stroke()
    setHasSignature(true)
  }

  const end = () => {
    setIsDrawing(false)
    if (hasSignature) {
      onSave(canvasRef.current!.toDataURL('image/png'))
    }
  }

  const clear = () => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!ctx || !canvas) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctx.strokeStyle = '#e0e0e0'
    for (let y = 0; y < height; y += 20) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
    }
    for (let x = 0; x < width; x += 20) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
    }
    setHasSignature(false)
    onSave('')
  }

  return (
    <div className="signature-canvas-wrapper" style={{ display: 'inline-block' }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{ display: 'block', cursor: 'crosshair', touchAction: 'none', maxWidth: '100%' }}
        onMouseDown={start}
        onMouseMove={draw}
        onMouseUp={end}
        onMouseLeave={end}
        onTouchStart={start}
        onTouchMove={draw}
        onTouchEnd={end}
      />
      <button
        type="button"
        onClick={clear}
        style={{
          marginTop: '8px',
          padding: '6px 16px',
          fontSize: '13px',
          color: '#6a6f73',
          background: '#f7f7f7',
          border: '1px solid #cecece',
          borderRadius: '6px',
          cursor: 'pointer',
        }}
      >
        🗑️ 清除签名
      </button>
      <style>{`
        .signature-canvas-wrapper { width: fit-content; }
      `}</style>
    </div>
  )
}
