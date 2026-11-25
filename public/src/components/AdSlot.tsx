'use client';
import { useEffect, useId, useRef } from 'react';

export type SlotKey = 'home_top' | 'home_middle' | 'home_bottom' | 'blog_feed';
export type SlotConfig = { slot_key: SlotKey; enabled: boolean; provider: 'yandex' | 'none'; block_id: string | null };

let loader: Promise<void> | undefined;
function loadYandex(): Promise<void> {
  if (loader) return loader;
  loader = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://yandex.ru/ads/system/context.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => { loader = undefined; reject(new Error('Ad loader unavailable')); };
    document.head.appendChild(script);
  });
  return loader;
}

declare global { interface Window {
  yaContextCb?: Array<() => void>;
  Ya?: { Context: { AdvManager: { render: (data: { blockId: string; renderTo: string }) => void } } };
} }

/** Preview never calls an ad network. Configuration comes from trusted server code. */
export function AdSlot({ config, preview = false }: { config: SlotConfig; preview?: boolean }) {
  const id = `ad-${useId().replace(/:/g, '')}`;
  const rendered = useRef(false);
  const valid = config.enabled && config.provider === 'yandex' && /^R-[A-Z]-\d+-\d+$/.test(config.block_id || '');
  useEffect(() => {
    if (preview || !valid || rendered.current) return;
    rendered.current = true;
    let active = true;
    loadYandex().then(() => {
      if (!active) return;
      window.yaContextCb ||= [];
      window.yaContextCb.push(() => { if (active) window.Ya?.Context.AdvManager.render({ blockId: config.block_id!, renderTo: id }); });
    }).catch(() => { rendered.current = false; });
    return () => { active = false; rendered.current = false; };
  }, [preview, valid, config.block_id, id]);
  if (!preview && !valid) return null;
  return <aside className={`ad-slot ad-slot-${config.slot_key}`} aria-label="Реклама">
    <span className="ad-label">Реклама</span>
    {preview ? <div className="ad-preview">Пример рекламного места · {config.slot_key}</div> : <div id={id} />}
  </aside>;
}
