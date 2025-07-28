'use client'

import dynamic from 'next/dynamic'

// Dynamically import the A2F visualizer to avoid SSR issues with Three.js
const A2FVisualizer = dynamic(() => import('../components/A2FVisualizer'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen flex items-center justify-center bg-transparent text-white">
      <div className="text-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-white mb-4"></div>
        <p>Loading A2F Visualizer...</p>
      </div>
    </div>
  )
})

export default function Home() {
  return (
      <main className="w-full min-h-screen">
        <A2FVisualizer />
      </main>
  )
}