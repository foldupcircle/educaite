'use client'

interface VideoPlayerProps {
  videoUrl: string | null
}

export default function VideoPlayer({ videoUrl }: VideoPlayerProps) {
  if (!videoUrl) {
    return <div>No video available</div>
  }

  return (
    <video controls className="w-full">
      <source src={videoUrl} type="video/webm" />
      Your browser does not support the video tag.
    </video>
  )
}

