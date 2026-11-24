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
