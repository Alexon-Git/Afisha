import { pageMetadata } from '../domain/seo';
import './globals.css';

export const dynamic = 'force-dynamic';
export function generateMetadata() {
  return pageMetadata('Бизнес Афиша — деловые мероприятия Новосибирска', 'Находите встречи, конференции и события для развития бизнеса.', '/');
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ru"><body>
    <a className="skip-link" href="#main">Перейти к содержимому</a>
    <header className="shell header"><a className="brand" href="/">Бизнес Афиша<span>Новосибирск</span></a>
      <nav aria-label="Основная навигация"><a href="/events">Все мероприятия <span aria-hidden="true">↗</span></a></nav></header>
    {children}
    <footer className="shell footer"><span>Бизнес Афиша · Новосибирск</span><a href="/events">Каталог мероприятий</a><span>Регистрация на сайтах организаторов</span></footer>
  </body></html>;
}
