// Extension loader for routes and cards.
// Downstream consumers can drop new files into this directory tree and the
// exports below will automatically include any modules that expose a `card`
// or `cards` export for cards, or a `route`/`routes` export for routes.
import { builtInCards } from './cards/builtInCards';

const modules = import.meta.glob('./**/*.{js,jsx,ts,tsx}', { eager: true });
const cards = [...builtInCards];

const routes = [];

const collect = (maybeItems, bucket) => {
  if (!maybeItems) return;
  const items = Array.isArray(maybeItems) ? maybeItems : [maybeItems];
  items.forEach((item) => bucket.push(item));
};

Object.values(modules).forEach((mod) => {
  collect(mod.card ?? mod.cards, cards);
  collect(mod.route ?? mod.routes, routes);
});

export { cards, routes };
