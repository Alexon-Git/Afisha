export function SiteFooter() {
  return <footer className="site-footer"><div className="shell footer-grid">
    <div><strong>Бизнес Афиша</strong><p>Деловые встречи Новосибирска: конференции, клубы, форумы и нетворкинг для предпринимателей.</p></div>
    <nav aria-label="Навигация в футере"><span>Разделы</span><a href="/">Главная</a><a href="/events">Каталог мероприятий</a><a href="/blog">Блог</a></nav>
    <div><span>Важно</span><p>Регистрация проходит на сайтах организаторов. Перед поездкой уточняйте дату и условия.</p></div>
  </div><div className="shell footer-bottom">© {new Date().getFullYear()} Бизнес Афиша · Новосибирск</div></footer>;
}
