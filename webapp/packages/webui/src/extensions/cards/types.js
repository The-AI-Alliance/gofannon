/**
 * @typedef {Object} CardActionContext
 * @property {(path: string) => void} navigate - Function used by cards to change routes.
 */

/**
 * @typedef {Object} CardExtension
 * @property {string} id - Globally unique card identifier.
 * @property {string} title - Display name shown to users.
 * @property {string} description - Short description of the card purpose.
 * @property {React.ReactElement} icon - Icon element rendered on the card.
 * @property {string} buttonText - Text shown in the action button.
 * @property {string} [buttonColor] - Optional button color (Material UI palette key).
 * @property {string} [iconColor] - Optional icon color (Material UI palette key).
 * @property {(context: CardActionContext) => void} onAction - Handler invoked when the user activates the card.
 * @property {string} [group] - Optional grouping label to cluster cards.
 * @property {number} [defaultOrder] - Default ordering hint for the registry.
 */

export {};