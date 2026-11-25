// ISO 4217 active codes, SIX list-one.xml, checked 2026-11-25.
const currencies = new Set('AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD BND BOB BOV BRL BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD USN UYI UYU UYW UZS VED VES VND VUV WST XAD XAF XAG XAU XBA XBB XBC XBD XCD XCG XDR XOF XPD XPF XPT XSU XTS XUA XXX YER ZAR ZMW ZWG'.split(' '));

interface Pricing {
  price?: number | null;
  price_kind?: string;
  price_amount?: string | null;
  price_max?: string | null;
  currency?: string | null;
}

function decimal(value?: string | null): { text: string; key: string } | null {
  if (typeof value !== 'string' || !/^\d{1,14}(?:\.\d{1,4})?$/.test(value)) return null;
  const [raw, fraction = ''] = value.split('.');
  const integer = raw.replace(/^0+(?=\d)/, '');
  const digits = fraction.replace(/0+$/, '');
  if (integer === '0' && !digits) return null;
  return {
    text: integer.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0') + (digits ? ',' + digits.padEnd(2, '0') : ''),
    key: integer.padStart(14, '0') + fraction.padEnd(4, '0'),
  };
}

/** Format decimal strings without ever converting monetary values to Number. */
export function formatEventPrice(input: Pricing | number | null): string {
  const event: Pricing = typeof input === 'object' && input !== null ? input : { price: input };
  // Old servers/fixtures without the new contract remain readable.
  if (event.price_kind === undefined) {
    const value = event.price;
    if (value === 0) return 'Бесплатно';
    if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) return 'Стоимость уточняется';
    return `${new Intl.NumberFormat('ru-RU').format(value)} ₽`;
  }
  const { price_kind: kind, currency } = event;
  if (['unknown','free','by_request'].includes(kind)) {
    if (event.price_amount != null || event.price_max != null || currency != null) return 'Стоимость уточняется';
    return kind === 'free' ? 'Бесплатно' : kind === 'by_request' ? 'По запросу' : 'Стоимость уточняется';
  }
  const low = decimal(event.price_amount);
  const high = decimal(event.price_max);
  if (!low || !currency || !currencies.has(currency)) return 'Стоимость уточняется';
  const suffix = currency === 'RUB' ? '₽' : currency;
  if (kind === 'range' && high && high.key >= low.key) return `${low.text}–${high.text} ${suffix}`;
  if (event.price_max != null) return 'Стоимость уточняется';
  if (kind === 'fixed') return `${low.text} ${suffix}`;
  if (kind === 'from') return `От ${low.text} ${suffix}`;
  return 'Стоимость уточняется';
}
