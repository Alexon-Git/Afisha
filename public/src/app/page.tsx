import { getBackendHealth } from '../api/server';

// Backend availability is checked at request time, never during image build.
export const dynamic = 'force-dynamic';

export default async function HomePage() {
  let connected = false;
  try { await getBackendHealth(); connected = true; } catch { /* Controlled fallback. */ }
  return <main id="main" className="shell main">
    <section className="hero">
      <p className="eyebrow">Деловая жизнь города</p>
      <h1>Место встречи<br />бизнеса и идей.</h1>
      <p className="intro">Готовим афишу деловых мероприятий Новосибирска: чтобы находить
        полезные встречи и переходить к регистрации у организатора.</p>
    </section>
    <section className="status-card" aria-labelledby="status-title">
      <span className="section-number" aria-hidden="true">01 / Статус</span>
      <h2 id="status-title">Публичный сайт в подготовке</h2>
      <p>Каталог и страницы мероприятий появятся на следующем этапе. Сейчас здесь технический каркас сайта.</p>
      <p className={connected ? 'connection online' : 'connection'} role="status">
        {connected ? 'Соединение с сервисом установлено' : 'Сервис временно недоступен. Попробуйте обновить страницу позже.'}
      </p>
    </section>
  </main>;
}
