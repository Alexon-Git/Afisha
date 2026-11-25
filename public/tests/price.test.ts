import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatEventPrice } from '../src/domain/price.ts';

for (const [price, expected] of [
  [0, 'Бесплатно'], [1, '1 ₽'], [500, '500 ₽'],
  [1500, '1\u00a0500 ₽'], [10000, '10\u00a0000 ₽'],
  [null, 'Стоимость уточняется'],
] as const) {
  test(`price ${price} has an explicit display value`, () => {
    assert.equal(formatEventPrice(price), expected);
  });
}

test('unsupported numeric data never invents a price', () => {
  for (const price of [-1, NaN, Infinity, -Infinity]) {
    assert.equal(formatEventPrice(price), 'Стоимость уточняется');
  }
});


for (const [kind, amount, max, currency, expected] of [
  ['unknown',null,null,null,'Стоимость уточняется'], ['free',null,null,null,'Бесплатно'],
  ['by_request',null,null,null,'По запросу'], ['fixed','1500',null,'RUB','1\u00a0500 ₽'],
  ['fixed','1500.50',null,'RUB','1\u00a0500,50 ₽'], ['fixed','20.50',null,'USD','20,50 USD'],
  ['from','1000',null,'RUB','От 1\u00a0000 ₽'], ['range','1000','2500','RUB','1\u00a0000–2\u00a0500 ₽'],
  ['fixed','99999999999999.9999',null,'EUR','99\u00a0999\u00a0999\u00a0999\u00a0999,9999 EUR'],
] as const) {
  test(`structured ${kind} ${amount} ${currency} keeps all digits`, () => {
    assert.equal(formatEventPrice({price_kind:kind,price_amount:amount,price_max:max,currency}),expected);
  });
}
test('invalid structured prices fail closed', () => {
  for (const price of [{price_kind:'free',price_amount:'1'}, {price_kind:'fixed',price_amount:'NaN',currency:'RUB'},
    {price_kind:'range',price_amount:'2',price_max:'1',currency:'USD'}, {price_kind:'fixed',price_amount:'1',currency:'ABC'}]) {
    assert.equal(formatEventPrice(price),'Стоимость уточняется');
  }
});
