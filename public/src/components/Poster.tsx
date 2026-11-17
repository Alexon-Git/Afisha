'use client';

import { useState } from 'react';
import { imagePath } from '../domain/safety';

export function Poster({ url, title }: { url: string | null; title: string }) {
  const [failed, setFailed] = useState(false);
  const source = imagePath(url);
  return <div className="poster">
    {source && !failed
      ? <img src={source} alt={`Афиша «${title}»`} loading="lazy" onError={() => setFailed(true)} width={720} height={480} />
      : <div className="poster-fallback" aria-label="Изображение отсутствует"><span>Бизнес<br />Афиша</span><span className="poster-city">Новосибирск</span></div>}
  </div>;
}
