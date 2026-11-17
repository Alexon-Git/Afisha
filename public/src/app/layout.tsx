import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Бизнес Афиша — Новосибирск',
  description: 'Деловые мероприятия Новосибирска. Публичный сайт в подготовке.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ru"><body>
    <a className="skip-link" href="#main">Перейти к содержимому</a>
    <header className="shell header"><a className="brand" href="/">Бизнес Афиша<span>Новосибирск</span></a>
      <span className="badge">Сайт в подготовке</span></header>
    {children}
    <footer className="shell footer">Деловые встречи начинаются с правильного выбора.</footer>
  </body></html>;
}
