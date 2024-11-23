'use client'

interface PDFViewerProps {
  pdfUrl: string | null
}

export default function PDFViewer({ pdfUrl }: PDFViewerProps) {
  console.log(pdfUrl)
  if (!pdfUrl) return null;
  
  return (
    <object
      data={pdfUrl}
      type="application/pdf"
      className="w-full h-[500px]"
    >
      <p>Unable to display PDF. <a href={pdfUrl}>Download</a> instead.</p>
    </object>
  );
}

