import type React from "react"
import "@/styles/globals.css"

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <title>arXivAgent</title>
        <meta name="description" content="AI-Powered arXiv Paper Assistant" />
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" sizes="72x72" href="/apple-icon-72x72.png" />
        <link rel="apple-touch-icon" sizes="114x114" href="/apple-icon-114x114.png" />
      </head>
      <body>
        {children}
      </body>
    </html>
  )
}

export const metadata = {
  title: 'arXivAgent',
  description: 'AI-Powered arXiv Paper Assistant',
  icons: {
    icon: '/favicon.ico',
    // 你也可以添加不同尺寸的图标
    apple: [
      { url: '/apple-icon.png' },
      { url: '/apple-icon-72x72.png', sizes: '72x72' },
      { url: '/apple-icon-114x114.png', sizes: '114x114' },
    ],
  },
}

