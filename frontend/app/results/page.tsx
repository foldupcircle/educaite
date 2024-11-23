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
    <div className="h-screen w-screen flex">
      <div className="w-1/2 h-full">
        {conversationUrl && (
          <iframe 
            src={conversationUrl}
            className="w-full h-full"
            allow="camera; microphone"
          />
        )}
      </div>
      <div className="w-1/2 h-full">
        <PDFViewer pdfUrl={pdfUrl} />
      </div>
    </div>
  )
}

