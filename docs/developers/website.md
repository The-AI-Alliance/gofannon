# Building the Website

This project uses [Docusaurus](https://docusaurus.io/) to build and maintain the documentation website.

## What is Docusaurus?

Docusaurus is an open-source static site generator built by Meta. It is designed specifically for building documentation websites and allows you to write content in Markdown, which is then compiled into a fast, optimized static website. Key features include:

- **Markdown-based content**: Write documentation in Markdown with support for MDX (Markdown + JSX)
- **Versioning**: Built-in support for documentation versioning
- **Search**: Integrated search functionality
- **Theming**: Customizable themes and styling
- **React-powered**: Build custom pages and components using React

## Prerequisites

- [Node.js](https://nodejs.org/) version 18.0 or higher

## Development

To run the website locally for development:

```bash
cd website
npm install
npm start
```

This will start a local development server at `http://localhost:3000` with hot reloading enabled.

## Building for Production

To build the static site for production:

```bash
cd website
npm run build
```

The built files will be output to the `website/build` directory.

## GitHub Pages Configuration

This repo supports GitHub Pages by switching the Docusaurus `url` and `baseUrl` when the `FOR_GH_PAGES` environment variable is set.

- **Local/dev builds**: Do nothing; defaults to `baseUrl: /`.
- **GitHub Pages builds**: Set `FOR_GH_PAGES=true` so the site builds under `/gofannon/`.

To preview a GitHub Pages-style build locally:

```bash
cd website
FOR_GH_PAGES=true npm run build
FOR_GH_PAGES=true npm run serve
```

The GitHub Actions workflow sets this variable during Pages deployments.

## Serving the Production Build

To preview the production build locally:

```bash
cd website
npm run serve
```

## Project Structure

- `website/docs/` - Documentation pages (auto-generated, do not edit directly)
- `website/blog/` - Blog posts
- `website/src/` - React components and custom pages
- `website/static/` - Static assets (images, etc.)
- `website/scripts/` - Build and sync scripts
- `website/docusaurus.config.ts` - Main configuration file
- `website/sidebars.ts` - Sidebar navigation configuration

## Documentation Sync

The documentation in `/docs` is the source of truth. The `website/docs/` directory is **auto-generated** and should not be edited directly.

### How It Works

A sync script (`website/scripts/sync-docs.js`) copies markdown files from `/docs` to `/website/docs` with the following transformations:

1. **Front matter injection** - Adds Docusaurus front matter (`title`, `sidebar_position`) to files that don't have it
2. **README → index rename** - Converts `README.md` files to `index.md` (Docusaurus convention for directory index pages)
3. **Category files** - Creates `_category_.json` files in subdirectories for sidebar organization
4. **Asset copying** - Copies non-markdown assets (images, etc.) as-is

### Sync Commands

```bash
# Sync docs manually
cd website
npm run sync-docs

# Start dev server (automatically syncs first)
npm start

# Build for production (automatically syncs first)
npm run build
```

### Important Notes

- **Do not edit `website/docs/` directly** - Changes will be overwritten on next sync
- **Edit `/docs/` instead** - All documentation changes should be made in the root `/docs` directory
- **`website/docs/` is gitignored** - The generated docs are not committed to version control
- **Sync runs automatically** - Both `npm start` and `npm run build` run the sync script first

### Customizing Sidebar Order

The sync script uses configuration to determine sidebar ordering:

- **Root files**: Edit `ROOT_POSITIONS` in `scripts/sync-docs.js`
- **Directory categories**: Edit `CATEGORY_CONFIG` in `scripts/sync-docs.js`
- **Individual files**: Add front matter with `sidebar_position` directly in `/docs/`

### Adding New Documentation

1. Create markdown files in `/docs/` (or subdirectories)
2. Run `npm run sync-docs` or `npm start` to regenerate
3. The sidebar will auto-update based on file structure

## Further Reading

For more information, see the [Docusaurus documentation](https://docusaurus.io/docs).