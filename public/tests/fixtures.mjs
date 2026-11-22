// Synthetic records for tests only. Never imported by application code.
/** @type {import('../src/api/types.ts').Event} */
export const fixture = {
  id: 1, title: 'Встреча предпринимателей', description: 'Практический разговор о развитии бизнеса.',
  datetime: '2099-12-15T18:30:00', location: 'Новосибирск, тестовая площадка',
  image_url: null, category_id: 1, category: { id: 1, name: 'Встречи', slug: 'meetings', is_active: true },
  price: 1500, rating: null, discount: null, payment_url: 'https://payments.example.test/wrong-target',
  creator_id: null, organizer_id: 1, organizer: { name: 'Тестовый клуб' },
  event_url: 'https://registration.example.test/event', source: 'https://source.example.test/event',
  verified_at: '2026-11-17T10:00:00Z', publication_status: 'published', event_status: 'scheduled',
};
export function fixtureEvents() {
  return [fixture,
    { ...fixture, id: 2, title: 'Отменённая встреча', event_status: 'cancelled' },
    { ...fixture, id: 3, title: 'Перенесённая встреча', event_status: 'postponed' },
    { ...fixture, id: 4, title: 'Скрытый черновик', publication_status: 'draft' },
    { ...fixture, id: 5, title: 'Скрытый архив', publication_status: 'archived' },
    { ...fixture, id: 6, title: 'AI </script><script>window.__injected=1</script>',
      description: '<script>window.__injected=1</script>', datetime: '2099-12-15T11:30:00Z',
      event_url: 'javascript:alert(1)', source: 'data:text/html,unsafe' },
    ...Array.from({ length: 97 }, (_, index) => ({ ...fixture, id: index + 100, title: `Тестовое событие ${index}` })),
  ];
}
