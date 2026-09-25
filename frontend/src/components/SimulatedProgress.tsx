import { useEffect, useState } from 'react'

interface SimulatedProgressProps {
  createdAt: string
  durationMs?: number
}

export default function SimulatedProgress({ createdAt, durationMs = 35000 }: SimulatedProgressProps) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const start = new Date(createdAt).getTime()

    const update = () => {
      const elapsed = Date.now() - start
      // Give it a slightly non-linear feel or just straight linear
      const raw = Math.floor((elapsed / durationMs) * 100)
      // Cap at 99% until it actually finishes
      setProgress(Math.max(0, Math.min(99, raw)))
    }

    update()
    const interval = setInterval(update, 800)
    return () => clearInterval(interval)
  }, [createdAt, durationMs])

  return <span>{progress}%</span>
}
