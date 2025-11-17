import defaultRoutesConfig from './defaultRoutes';
import overrideRoutesConfig from './overrides';

const normalizeRoutes = (config) => ({
  routes: Array.isArray(config?.routes) ? config.routes : [],
});

const mergeRouteEntry = (baseRoute = {}, overrideRoute = {}) => ({
  ...baseRoute,
  ...overrideRoute,
  children: mergeRoutesList(baseRoute.children, overrideRoute.children),
});

export const mergeRoutesList = (baseRoutes = [], overrideRoutes = []) => {
  const base = Array.isArray(baseRoutes) ? baseRoutes : [];
  const override = Array.isArray(overrideRoutes) ? overrideRoutes : [];

  const mergedMap = new Map(
    base.map((route, index) => [route.id || route.path || `base-${index}`, { ...route }]),
  );

  override.forEach((route) => {
    if (!route?.id && !route?.path) return;
    const key = route.id || route.path;
    const current = mergedMap.get(key) || {};
    mergedMap.set(key, mergeRouteEntry(current, route));
  });

  return Array.from(mergedMap.values());
};

export const mergeRoutesConfig = (baseConfig, overrideConfig) => {
  const base = normalizeRoutes(baseConfig);
  const override = normalizeRoutes(overrideConfig);

  return { routes: mergeRoutesList(base.routes, override.routes) };
};

export const loadRoutesConfig = () => mergeRoutesConfig(defaultRoutesConfig, overrideRoutesConfig);

export default loadRoutesConfig;
