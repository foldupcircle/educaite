'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import PDFViewer from '@/components/PDFViewer'

export default function ResultsPage() {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [conversationUrl, setConversationUrl] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedPdfUrl = localStorage.getItem('pdfUrl')
      const storedConversationUrl = localStorage.getItem('conversation_url')
      
      if (!storedPdfUrl || !storedConversationUrl) {
        router.push('/')
      } else {
        setPdfUrl(storedPdfUrl)
        setConversationUrl(storedConversationUrl)
      }
    }
  }, [router])

  return (
    <div className="fixed inset-0 flex">
      <div className="w-1/2 h-screen">
        {conversationUrl && (
          <iframe 
            src={conversationUrl}
            className="w-full h-full border-0"
            allow="camera; microphone"
            style={{ aspectRatio: '9/16' }}
          />
        )}
      </div>
      <div className="w-1/2 h-screen">
        <PDFViewer pdfUrl={pdfUrl} />
      </div>
    </div>
  )
}

