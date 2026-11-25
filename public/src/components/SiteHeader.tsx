/** Static navigation: the header must not call the API, so invalid links never reach the backend. */
const links: [string, string][] = [['/events', 'Все события'], ['/events?date=today', 'Сегодня'], ['/events?date=tomorrow', 'Завтра'], ['/events?date=weekend', 'Выходные']];

export function SiteHeader() {
  return <header className="site-header">
    <div className="shell header"><a className="brand" href="/">Бизнес Афиша<span>деловые мероприятия</span></a>
      <div className="header-right"><span className="city"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></svg>Новосибирск</span></div></div>
    <nav className="shell category-nav" aria-label="Основная навигация">{links.map(([href, label]) => <a key={href} href={href}>{label}</a>)}</nav>
  </header>;
}
