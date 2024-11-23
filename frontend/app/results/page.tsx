'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import PDFViewer from '@/components/PDFViewer'
import VideoPlayer from '@/components/VideoPlayer'

export default function ResultsPage() {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedPdfUrl = localStorage.getItem('pdfUrl')
      const storedVideoUrl = localStorage.getItem('recordedVideoUrl')
      
      if (!storedPdfUrl || !storedVideoUrl) {
        router.push('/')
      } else {
        setPdfUrl(storedPdfUrl)
        setVideoUrl(storedVideoUrl)
      }
    }
  }, [router])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-4xl">
        <h1 className="text-2xl font-bold mb-6 text-center">Results</h1>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="w-full md:w-1/2">
            <h2 className="text-xl font-semibold mb-2">Your Explanation</h2>
            <VideoPlayer videoUrl={videoUrl} />
          </div>
          <div className="w-full md:w-1/2">
            <h2 className="text-xl font-semibold mb-2">Your Homework</h2>
            <PDFViewer pdfUrl={pdfUrl} />
          </div>
        </div>
      </div>
    </div>
  )
}

