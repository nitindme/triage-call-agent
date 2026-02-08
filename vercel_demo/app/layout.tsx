import './globals.css'

export const metadata = {
  title: 'Demo Checkout - AI Incident Triage',
  description: 'Demo checkout page that shows the bug',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
