'use client'

interface PDFViewerProps {
  pdfUrl: string | null
}

export default function PDFViewer({ pdfUrl }: PDFViewerProps) {
  if (!pdfUrl) return null;
  
  return (
    <object
      data={pdfUrl}
      type="application/pdf"
      className="w-full h-full"
      style={{ minHeight: '100vh' }}
    >
      <p>Unable to display PDF. <a href={pdfUrl}>Download</a> instead.</p>
    </object>
  );
}

