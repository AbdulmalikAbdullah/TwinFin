import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'التوأم | شريكك المالي بالذكاء الاصطناعي',
  description: 'تجربة مالية عصرية تساعدك على فهم القرارات المالية قبل الإنفاق.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
