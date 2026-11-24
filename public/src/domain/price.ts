const rubles = new Intl.NumberFormat('ru-RU');

/** Current MVP: zero is free; null or unsupported data is an unknown price. */
export function formatEventPrice(price: number | null): string {
  if (price === null || !Number.isFinite(price) || price < 0) return 'Стоимость уточняется';
  if (price === 0) return 'Бесплатно';
  return `${rubles.format(price)} ₽`;
}
