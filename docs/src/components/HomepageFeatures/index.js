import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Singer Simplified',
    Svg: require('@site/static/img/singer-logo.svg').default,
    description: (
      <>
        Like Meltano, <b>Alto</b> wraps <a href="https://www.singer.io/">Singer</a> allowing you to centrally manage your
        configuration. Under the hood, Alto will do <i>everything</i> from building and
        caching <a href="https://github.com/pantsbuild/pex">PEX</a> plugins per integration
        to managing catalog, state, and execution. Integrate hunreds of data sources in minutes without <i>any</i> code.
        Prior art from Meltano makes the format familiar.
      </>
    ),
  },
  {
    title: 'Minimalist by design',
    Svg: require('@site/static/img/cloud-logo-1.svg').default,
    description: (
      <>
        Alto is designed, purposefully, to be as simple as possible. We believe
        that the best tools are the ones that get out of your way. We've tried to
        keep the number of concepts to a minimum and we leverage the power of
        <a href="https://www.dynaconf.com/"> Dynaconf</a>,
        <a href="https://pydoit.org/"> Doit</a>,
        <a href="https://github.com/pantsbuild/pex"> PEX</a>,
         and <a href="https://filesystem-spec.readthedocs.io/en/latest/">fsspec </a>
        to do the heavy lifting. This has allowed us to rapidly iterate on features
        such as the Data Reservoir. It is <i>fast</i>, <code>alto list --all</code> and see.
      </>
    ),
  },
  {
    title: 'Powered by Doit',
    Svg: require('@site/static/img/python-logo.svg').default,
    description: (
      <>
        Alto has opted for a Makefile-like approach for its execution model. This
        means that you simply tell Alto what you want to do and it will figure out
        the rest. Alto is built on top of <a href="https://pydoit.org/">Doit</a> which
        is a pure python task management & automation tool. You can even include your
        own custom tasks via the extension system.
      </>
    ),
  },
];

function Feature({Svg, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
