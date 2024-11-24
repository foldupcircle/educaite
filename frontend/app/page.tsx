'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'

// const isDev = process.env.NODE_ENV !== 'production'

// const baseUrl = isDev ? process.env.NEXT_PUBLIC_DEV_URL : process.env.NEXT_PUBLIC_PROD_URL
const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL
// const baseUrl = 'https://app.explainstein.com'
// const baseUrl = 'http://localhost:8000'

export default function Home() {
  const [name, setName] = useState('')
  const [pdf, setPdf] = useState<File | null>(null)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (name && pdf) {
      // Store in localStorage for client-side use
      const reader = new FileReader()
      reader.onload = (e) => {
        localStorage.setItem('userName', name)
        localStorage.setItem('pdfUrl', e.target?.result as string)
      }
      reader.readAsDataURL(pdf)

      // Send to backend
      try {
        const formData = new FormData()
        formData.append('name', name)
        formData.append('file', pdf)

        const response = await axios.post(`${baseUrl}/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })

        if (response.status !== 200) {
          throw new Error('Failed to upload')
        }

        const data = response.data
        console.log('data', data)
        localStorage.setItem('context', data.context)
        // router.push('/record')
      } catch (error) {
        console.error('Error uploading:', error)
      }

      
      const existingContext = localStorage.getItem('context') || '';
      // const userContext = localStorage.getItem('userContext') || '';
      // console.log('userContext', userContext)
      console.log('existingContext', existingContext)
      // const updatedContext = `${existingContext}\n\n# Student's Current Situation Context:\n${userContext}`;
      try {
        const conversationResponse = await axios.post(`${baseUrl}/create_conversation`, {
          context: existingContext
        }, {
          headers: {
            'Content-Type': 'application/json'
          }
        });
        const conversationData = conversationResponse.data;
        localStorage.setItem('conversation_url', conversationData.conversation_url);
      } catch (error) {
        if (axios.isAxiosError(error)) {
          if (error.response?.status === 422) {
            console.error('Validation error:', error.response.data);
            // Handle the validation error appropriately
          }
        }
        console.error('Error creating conversation:', error);
        return;
      }
      console.log('Successfully uploaded recording')
      router.push('/results')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">Homework Helper</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Your Name
            </label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label htmlFor="pdf" className="block text-sm font-medium text-gray-700">
              Upload Homework (PDF)
            </label>
            <input
              type="file"
              id="pdf"
              accept=".pdf"
              onChange={(e) => setPdf(e.target.files?.[0] || null)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Start
          </button>
        </form>
      </div>
    </div>
  )
}

