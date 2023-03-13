// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Alto Documentation',
  tagline: 'Lightweight EL',
  favicon: 'img/favicon.ico',

  url: 'https://z3z1ma.github.io',
  baseUrl: '/alto/',

  // GitHub pages deployment config.
  organizationName: 'z3z1ma',
  projectName: 'alto',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl:
            'https://github.com/z3z1ma/alto/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/docusaurus-social-card.jpg',
      navbar: {
        title: 'Alto',
        logo: {
          alt: 'Alto Logo',
          src: 'img/alto-logo.png',
        },
        items: [
          {
            type: 'doc',
            docId: 'intro',
            position: 'left',
            label: 'Tutorial',
          },
          {
            to: '/docs/concepts/intro',
            label: 'Concepts',
            position: 'left'
          },
          {
            to: '/docs/integrations/intro',
            label: 'Integrations',
            position: 'left'
          },
          {
            to: '/docs/integrations/extensions',
            label: 'Extensions',
            position: 'left'
          },
          {
            href: 'https://github.com/z3z1ma/alto',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                to: '/docs/intro',
                label: 'Tutorial',
              },
              {
                to: '/docs/integrations/intro',
                label: 'Integrations',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'dbt Slack',
                href: 'https://twitter.com/dbt_labs',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'z3z1ma GitHub',
                href: 'https://github.com/z3z1ma',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Alex Butler. Built with Docusaurus.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
        additionalLanguages: ['toml'],
      },
    }),
};

module.exports = config;
