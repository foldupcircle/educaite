'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'

export default function RecordPage() {
  const [isRecording, setIsRecording] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const router = useRouter()

  useEffect(() => {
    if (typeof window !== 'undefined' && !localStorage.getItem('userName')) {
      router.push('/')
    }
  }, [router])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          setRecordedBlob(event.data)
        }
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
    } catch (error) {
      console.error('Error accessing media devices:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const handleNext = async () => {
    if (recordedBlob) {
      localStorage.setItem('recordedVideoUrl', URL.createObjectURL(recordedBlob))
      const formData = new FormData()
      formData.append('file', recordedBlob, 'recording.webm')
      formData.append('description', '')

      try {
        const response = await axios.post('http://localhost:8000/record', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
        console.log('Transcription:', response.data['transcription'])
        console.log('Analysis:', response.data['analysis'])
        
        if (response.status !== 200) {
          throw new Error('Failed to upload recording')
        }
      } catch (error) {
        console.error('Error uploading recording:', error)
        return
      }
      console.log('Successfully uploaded recording')
      router.push('/results')
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96 space-y-4">
        <h1 className="text-2xl font-bold mb-6 text-center">Record Your Explanation</h1>
        
        {typeof window !== 'undefined' && localStorage.getItem('conversation_url') && (
          <iframe 
            src={localStorage.getItem('conversation_url') || ''} 
            width="100%" 
            height="600px"
            className="mb-4"
          />
        )}

        <p className="text-center text-gray-600">
          Explain where you are in your homework and what you&apos;re struggling with.
        </p>
        <div className="flex justify-center">
          {!isRecording ? (
            <button
              onClick={startRecording}
              className="py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Start Recording
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="py-2 px-4 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              Stop Recording
            </button>
          )}
        </div>
        {recordedBlob && (
          <button
            onClick={handleNext}
            className="w-full py-2 px-4 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            Next
          </button>
        )}
      </div>
    </div>
  )
}

