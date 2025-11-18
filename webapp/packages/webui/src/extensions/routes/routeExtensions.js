// Allows external repositories to extend or replace the default application routes.
// The function should return the final array of route definitions.
// Each route uses the shape defined in `src/config/routesConfig.js`.
export const extendRoutes = (defaultRoutes = []) => defaultRoutes;

export default extendRoutes;
