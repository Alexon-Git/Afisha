import { pageMetadata } from '../domain/seo';
import { SiteHeader } from '../components/SiteHeader';
import { SiteFooter } from '../components/SiteFooter';
import './globals.css';

export const dynamic = 'force-dynamic';
export function generateMetadata() {
  return pageMetadata('Бизнес Афиша — деловые мероприятия Новосибирска', 'Находите встречи, конференции и события для развития бизнеса.', '/');
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ru"><body>
    <a className="skip-link" href="#main">Перейти к содержимому</a>
    <SiteHeader />
    {children}
    <SiteFooter />
  </body></html>;
}
