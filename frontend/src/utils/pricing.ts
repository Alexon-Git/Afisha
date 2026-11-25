// ISO 4217 active codes, SIX list-one.xml, checked 2026-11-25.
const currencies = new Set('AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD BND BOB BOV BRL BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD USN UYI UYU UYW UZS VED VES VND VUV WST XAD XAF XAG XAU XBA XBB XBC XBD XCD XCG XDR XOF XPD XPF XPT XSU XTS XUA XXX YER ZAR ZMW ZWG'.split(' '));

export interface Pricing {
  price?: number | null;
  price_kind?: 'unknown' | 'free' | 'fixed' | 'from' | 'range' | 'by_request';
  price_amount?: string | null;
  price_max?: string | null;
  currency?: string | null;
}
export const pricingFields = ['price_kind', 'price_amount', 'price_max', 'currency'] as const;
export function pricingFromEvent(event: Pricing): Pricing {
  if (event.price_kind !== undefined) return Object.fromEntries(pricingFields.map(key => [key, event[key]]));
  return event.price == null ? { price_kind: 'unknown' } : event.price === 0 ? { price_kind: 'free' }
    : { price_kind: 'fixed', price_amount: String(event.price), currency: 'RUB' };
}
function canonical(value?: string | null): string | null {
  if (value == null || value === '') return null;
  if (!/^\d{1,14}(?:\.\d{1,4})?$/.test(value)) throw new Error('Сумма: до 14 цифр и 4 знаков после точки');
  const [whole, fraction = ''] = value.split('.');
  const normalized = whole.replace(/^0+(?=\d)/, '') + (fraction.replace(/0+$/, '') ? '.' + fraction.replace(/0+$/, '') : '');
  if (normalized === '0') throw new Error('Сумма должна быть положительной; для бесплатного события выберите «Бесплатно»');
  return normalized;
}
export function pricingPayload(data: Pricing): Pricing {
  const kind = data.price_kind || 'unknown';
  if (['unknown','free','by_request'].includes(kind)) return { price_kind: kind, price_amount: null, price_max: null, currency: null };
  const low = canonical(data.price_amount);
  const high = kind === 'range' ? canonical(data.price_max) : null;
  const key = (value: string) => { const [a,b=''] = value.split('.'); return a.padStart(14,'0') + b.padEnd(4,'0'); };
  if (!low || !data.currency || !currencies.has(data.currency) || (kind === 'range' && (!high || key(high) < key(low)))) {
    throw new Error('Укажите положительную сумму, валюту ISO 4217 и корректный диапазон');
  }
  return { price_kind: kind, price_amount: low, price_max: high, currency: data.currency };
}
