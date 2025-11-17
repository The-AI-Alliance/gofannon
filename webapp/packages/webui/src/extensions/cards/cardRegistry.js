import { registerBuiltInCards } from './builtInCards';
import loadCardsConfig from './config/configLoader';

const cardRegistry = new Map();
const externalRegistrars = [];
let initialized = false;
let externalApplied = false;

export const registerCard = (card) => {
  if (!card || !card.id) {
    throw new Error('Card registration requires a valid id');
  }

  if (cardRegistry.has(card.id)) {
    console.warn(`Overwriting existing card registration for id: ${card.id}`);
  }

  const normalizedCard = {
    buttonColor: 'primary',
    iconColor: 'inherit',
    ...card,
  };

  cardRegistry.set(card.id, normalizedCard);
  return normalizedCard;
};

export const registerExternalCardRegistrar = (registrar) => {
  if (typeof registrar === 'function') {
    externalRegistrars.push(registrar);
  }
};

const applyExternalRegistrars = () => {
  if (externalApplied) return;

  const windowRegistrars =
    typeof window !== 'undefined' && Array.isArray(window.__CARD_EXTENSION_REGISTRARS__)
      ? window.__CARD_EXTENSION_REGISTRARS__
      : [];

  [...windowRegistrars, ...externalRegistrars].forEach((registrar) => {
    try {
      registrar({ registerCard });
    } catch (error) {
      console.warn('Failed to apply card registrar', error);
    }
  });

  externalApplied = true;
};

export const ensureCardRegistryInitialized = () => {
  if (initialized) return;

  registerBuiltInCards(registerCard);
  applyExternalRegistrars();
  initialized = true;
};

export const listCards = (cardConfig = loadCardsConfig()) => {
  ensureCardRegistryInitialized();

  const configMap = new Map(
    (cardConfig.cards || []).map((card, index) => [card.id, { defaultOrder: index, ...card }]),
  );

  const cards = Array.from(cardRegistry.values())
    .filter((card) => {
      const settings = configMap.get(card.id);
      if (settings && settings.enabled === false) {
        return false;
      }
      return true;
    })
    .map((card) => {
      const settings = configMap.get(card.id) || {};
      return {
        ...card,
        group: settings.group || card.group,
        order: settings.order ?? settings.defaultOrder ?? card.defaultOrder ?? Number.MAX_SAFE_INTEGER,
      };
    })
    .sort((a, b) => {
      const orderDiff = (a.order ?? 0) - (b.order ?? 0);
      if (orderDiff !== 0) return orderDiff;
      return a.title.localeCompare(b.title);
    });

  return cards;
};

export const getCardById = (cardId) => cardRegistry.get(cardId);

export const clearCardRegistry = () => {
  cardRegistry.clear();
  initialized = false;
  externalApplied = false;
};

export default cardRegistry;