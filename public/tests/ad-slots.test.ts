import test from 'node:test';
import assert from 'node:assert/strict';
import { getAdSlot } from '../src/domain/adSlots.ts';

test('ad slots are disabled unless explicitly enabled with a valid block ID', () => {
  const previous = [process.env.AD_ENABLED, process.env.AD_HOME_TOP_BLOCK_ID];
  try {
    delete process.env.AD_ENABLED;
    process.env.AD_HOME_TOP_BLOCK_ID = 'R-A-123-45';
    assert.equal(getAdSlot('home_top').enabled, false);
    process.env.AD_ENABLED = 'true';
    process.env.AD_HOME_TOP_BLOCK_ID = '<script>alert(1)</script>';
    assert.equal(getAdSlot('home_top').enabled, false);
    process.env.AD_HOME_TOP_BLOCK_ID = 'R-A-123-45';
    assert.equal(getAdSlot('home_top').enabled, true);
    assert.equal(getAdSlot('blog_feed').enabled, false);
  } finally {
    const [enabled, block] = previous;
    if (enabled === undefined) delete process.env.AD_ENABLED; else process.env.AD_ENABLED = enabled;
    if (block === undefined) delete process.env.AD_HOME_TOP_BLOCK_ID; else process.env.AD_HOME_TOP_BLOCK_ID = block;
  }
});
