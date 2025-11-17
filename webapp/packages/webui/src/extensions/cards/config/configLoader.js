import defaultCardsConfig from './defaultCardsConfig';

const normalizeCards = (config) => ({ cards: Array.isArray(config?.cards) ? config.cards : [] });

export const mergeCardsConfig = (baseConfig, overrideConfig) => {
  const base = normalizeCards(baseConfig);
  const override = normalizeCards(overrideConfig);

  const mergedMap = new Map(base.cards.map((card) => [card.id, { ...card }]));
  override.cards.forEach((entry) => {
    if (!entry?.id) return;
    const current = mergedMap.get(entry.id) || {};
    mergedMap.set(entry.id, { ...current, ...entry });
  });

  return { cards: Array.from(mergedMap.values()) };
};

export const parseCardsConfigOverride = (rawValue) => {
  if (!rawValue) return { cards: [] };

  try {
    if (typeof rawValue === 'string') {
      return JSON.parse(rawValue);
    }

    if (typeof rawValue === 'object') {
      return rawValue;
    }
  } catch (error) {
    console.warn('Unable to parse card configuration override. Falling back to defaults.', error);
  }

  return { cards: [] };
};

const resolveOverrideCandidates = () => {
  const fromWindow = typeof window !== 'undefined' ? window.__CARD_CONFIG_OVERRIDES__ : undefined;
  const envOverride = import.meta?.env?.VITE_CARD_CONFIG_OVERRIDES;
  const nodeEnvOverride = typeof process !== 'undefined' ? process.env?.CARD_CONFIG_OVERRIDES : undefined;

  return [envOverride, nodeEnvOverride, fromWindow].filter((value) => value !== undefined);
};

export const loadCardsConfig = () => {
  const overrides = resolveOverrideCandidates()
    .map(parseCardsConfigOverride)
    .reduce((currentConfig, parsedOverride) => mergeCardsConfig(currentConfig, parsedOverride), { cards: [] });

  return mergeCardsConfig(defaultCardsConfig, overrides);
};

export default loadCardsConfig;