import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Bolsa de Trabajo | Empleos remotos y presenciales',
  description:
    'Encuentra ofertas de empleo remoto y presencial actualizadas a diario. Filtra por modalidad, país y tecnología.',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="es">
      <body className="antialiased">{children}</body>
    </html>
  )
}