import type { SlotConfig, SlotKey } from '../components/AdSlot';
const envKeys: Record<SlotKey, string> = {
  home_top: 'AD_HOME_TOP_BLOCK_ID', home_middle: 'AD_HOME_MIDDLE_BLOCK_ID',
  home_bottom: 'AD_HOME_BOTTOM_BLOCK_ID', blog_feed: 'AD_BLOG_FEED_BLOCK_ID',
};
/** Server-controlled configuration. Unknown IDs fail closed. */
export function getAdSlot(slot_key: SlotKey): SlotConfig {
  const block_id = process.env[envKeys[slot_key]] || null;
  const enabled = process.env.AD_ENABLED === 'true' && /^R-[A-Z]-\d+-\d+$/.test(block_id || '');
  return { slot_key, enabled, provider: enabled ? 'yandex' : 'none', block_id: enabled ? block_id : null };
}
