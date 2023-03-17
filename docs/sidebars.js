/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */

// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  tutorialSidebar: [
    'intro',
    'familiarize',
    {
      type: 'category',
      label: 'Alto Fundamentals',
      collapsed: false,
      items: [
        'tutorial-basics/create-a-project',
        'tutorial-basics/example-configuration',
        'tutorial-basics/environments',
        'tutorial-basics/secret-management',
        'tutorial-basics/project-configuration',
        'tutorial-basics/plugin-configuration',
        'tutorial-basics/tap-configuration',
        'tutorial-basics/target-configuration',
        'tutorial-basics/utility-configuration',
      ],
    },
    'cli',
  ],
  conceptsSidebar: [],
  integrationsSidebar: [
    'integrations/intro',
    'integrations/taps',
    'integrations/targets',
  ],
  extensionsSidebar: [
    'extensions/intro',
    'extensions/evidence',
    'extensions/rill',
  ],
};

module.exports = sidebars;
