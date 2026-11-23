import React, { useCallback, useEffect, useRef, useState } from 'react';
import { importApi, ImportCandidate, ImportRun, ImportSource } from '../services/api';
import { instantToEventInput } from '../utils/eventTime';

const newKey = () => `import_${Date.now()}_${Math.random().toString(36).slice(2)}`;
const errorText = (e: any) => typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Не удалось выполнить действие. Обновите данные и проверьте поля.';

export default function ImportDashboard() {
  const [sources,setSources] = useState<ImportSource[]>([]);
  const [runs,setRuns] = useState<ImportRun[]>([]);
  const [candidates,setCandidates] = useState<ImportCandidate[]>([]);
  const [selected,setSelected] = useState<ImportCandidate|null>(null);
  const [page,setPage] = useState(1);
  const [pages,setPages] = useState(1);
  const [sourceId,setSourceId] = useState('');
  const [url,setUrl] = useState('');
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  const [busy,setBusy] = useState(false);
  const [dismissed,setDismissed] = useState(false);
  const [note,setNote] = useState('');
  const [target,setTarget] = useState('');
  const [time,setTime] = useState('');
  const [city,setCity] = useState('');
  const [venue,setVenue] = useState('');
  const key = useRef(newKey());
  const requestIdentity = useRef('');
  const refresh = useCallback(async () => {
    const [s,r,c] = await Promise.all([importApi.sources(),importApi.runs(),importApi.candidates(page)]);
    setSources(s.data); setRuns(r.data); setCandidates(c.data.items); setPages(c.data.total_pages);
  },[page]);
  useEffect(() => {
    let active=true;
    refresh().catch(e => { if(active) setError(errorText(e)); });
    return () => {active=false;};
  },[refresh]);
  useEffect(() => {
    if (!runs.some(r => ['queued','running'].includes(r.status))) return;
    const timer = setInterval(() => { refresh().catch(e => setError(errorText(e))); },5000);
    return () => clearInterval(timer);
  },[runs,refresh]);
  const choose = (c: ImportCandidate) => {
    setSelected(c); setDismissed(false); setTarget(''); setNote('');
    setTime(c.start_at || ''); setCity(c.city || ''); setVenue(c.venue_name || '');
  };
  const act = async (operation: () => Promise<any>, message = '') => {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await operation();
      if (result?.data?.revision) choose(result.data);
      setNotice(message); await refresh();
    } catch(e) { setError(errorText(e)); }
    finally { setBusy(false); }
  };
  return <main className="max-w-7xl mx-auto p-6 space-y-4">
    <a href="/admin/">К мероприятиям</a><h1 className="text-2xl font-bold">Импорт мероприятий</h1>
    <p>Импорт создаёт кандидатов. Одобрение не публикует мероприятие. Новый Event создаётся только как непроверенный черновик.</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <fieldset disabled={busy}><legend>Разрешённые источники</legend>
      <ul>{sources.map(s => <li key={s.id}>{s.name}: {s.state}; основание: {s.permission_basis || 'не подтверждено'}; проверка до {s.review_due_at || 'не указана'}; robots: {s.robots_state}</li>)}</ul>
      {!sources.length && <p>Разрешённых источников пока нет. Live-импорт ждёт подтверждения условий.</p>}
      <label>Источник<select value={sourceId} onChange={e => setSourceId(e.target.value)}><option value="">Выберите источник</option>{sources.map(s => <option key={s.id} value={s.id} disabled={s.state!=='enabled'}>{s.name}</option>)}</select></label>
      <label>URL страницы<input type="url" value={url} onChange={e => setUrl(e.target.value)} /></label>
      <button disabled={!sourceId || !url} onClick={() => act(async () => {
        const identity=sourceId+url;
        if(requestIdentity.current!==identity) { key.current=newKey(); requestIdentity.current=identity; }
        const result=await importApi.start(Number(sourceId),url,key.current);
        key.current=newKey(); return result;
      },'Запуск поставлен в очередь')}>Запустить импорт</button>
    </fieldset>
    <h2>Запуски (последние 20)</h2><ul>{runs.map(r => <li key={r.id}>{r.id}: {r.status}; записей {r.records_seen}, новых {r.candidates_created}; {r.error_code || ''}
      {r.record_errors.map((e,i) => <span key={i}> Попытка {e.attempt}: {e.code}</span>)}</li>)}</ul>
    <h2>Кандидаты</h2><ul>{candidates.map(c => <li key={c.id}><button disabled={busy} onClick={() => act(async () => {choose((await importApi.candidate(c.id)).data);})}>{c.title || 'Без названия'} — {c.review_status}</button></li>)}</ul>
    <button disabled={busy || page<=1} onClick={() => setPage(page-1)}>Назад</button><span>Страница {page}</span><button disabled={busy || page>=pages} onClick={() => setPage(page+1)}>Далее</button>
    {selected && <fieldset disabled={busy}><legend>Кандидат #{selected.id}, revision {selected.revision}</legend>
      <p>{selected.title} — {selected.review_status}; Event: {selected.linked_event_id || 'не создан'}</p>
      <p>Источник: {selected.source_url}; исходная дата: {selected.original_start || 'нет'}; {selected.time_resolution}</p>
      <p>Время Новосибирска: {selected.start_at ? instantToEventInput(selected.start_at) : 'Неоднозначно — требуется явный offset'}</p>
      <p>Организатор (предложение): {selected.organizer_name || 'не указан'}; {selected.organizer_url || ''}. Сопоставление Organizer выполняется отдельно, контакт не импортируется.</p>
      <p>Ссылка мероприятия: {selected.official_event_url || 'не указана'}; цена: {selected.price_kind} {selected.price_amount ?? 'неизвестна'} {selected.currency || ''}; состояние из источника: {selected.proposed_event_status || 'не указано'}.</p>
      <p>Предупреждения: {selected.warnings.join(', ')}</p><pre>{JSON.stringify(selected.field_provenance,null,2)}</pre>
      <h3>Возможные дубли</h3><ul>{selected.matches.map(m => <li key={m.id}>Event {m.event_id || 'удалён'}: {m.reason_codes.join(', ')}; score {m.score}</li>)}</ul>
      <label><input type="checkbox" checked={dismissed} onChange={e => setDismissed(e.target.checked)} />Подтверждаю: все показанные совпадения не являются дублями</label>
      <label>Примечание редактора<input value={note} onChange={e => setNote(e.target.value)} /></label>
      <label>Дата ISO 8601 с offset<input value={time} onChange={e => setTime(e.target.value)} placeholder="2026-11-23T18:00:00+07:00" /></label>
      <label>Город<input value={city} onChange={e => setCity(e.target.value)} /></label>
      <label>Место<input value={venue} onChange={e => setVenue(e.target.value)} /></label>
      <button onClick={() => act(() => importApi.edit(selected,{start_at:time,city,venue_name:venue,review_note:note}))}>Уточнить факты (снять одобрение)</button>
      <button disabled={!['pending','needs_review'].includes(selected.review_status)} onClick={() => act(() => importApi.approve(selected,dismissed),'Кандидат одобрен, не опубликован')}>Одобрить</button>
      <button disabled={!note.trim() || !['pending','needs_review'].includes(selected.review_status)} onClick={() => act(() => importApi.reject(selected,note))}>Отклонить</button>
      <button disabled={selected.review_status!=='approved'} onClick={() => act(() => importApi.promote(selected),'Создан черновик. Проверка и публикация — в редакторском процессе мероприятия.')}>Создать Event draft</button>
      <label>ID существующего Event<input type="number" min="1" value={target} onChange={e => setTarget(e.target.value)} /></label>
      <button disabled={selected.review_status!=='approved' || !Number.isInteger(Number(target)) || Number(target)<1} onClick={() => act(() => importApi.link(selected,Number(target)),'Связь сохранена; существующее мероприятие не изменено')}>Привязать к Event</button>
      <button onClick={() => act(() => importApi.recheck(selected,newKey()),'Повторная проверка в очереди')}>Повторно проверить источник</button>
    </fieldset>}
  </main>;
}
